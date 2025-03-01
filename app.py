from flask import Flask, jsonify, render_template, request
from abc import ABC, abstractmethod
import psutil
import threading
import requests
import sqlite3
import time
import csv
from config import Config

app = Flask(__name__)
config = Config()

# Abstract Collector Interface
class MetricData:
    def __init__(self, device_id: str, metric_type: str, values: dict):
        self.device_id = device_id
        self.metric_type = metric_type
        self.values = values
        self.timestamp = time.time()

# Update CollectorInterface to use MetricData
class CollectorInterface(ABC):
    @abstractmethod
    def get_device_id(self) -> str:
        pass

    @abstractmethod
    def get_metric_type(self) -> str:
        pass
    
    @abstractmethod
    def collect(self) -> MetricData:
        pass

# PC Metrics Collector
class PCCollector(CollectorInterface):
    def get_device_id(self) -> str:
        return "device_1"
    
    def get_metric_type(self) -> str:
        return "system_metrics"

    def collect(self) -> MetricData:
        ram_usage = psutil.virtual_memory().percent
        # Handle cloud environment where battery isn't available
        battery_info = {"percent": 0, "status": "Cloud Server - No Battery"}
        
        try:
            battery = psutil.sensors_battery()
            if battery:
                battery_info = {
                    "percent": battery.percent,
                    "status": "Connected" if battery.power_plugged else "Discharging"
                }
        except Exception:
            pass
            
        return MetricData(
            self.get_device_id(),
            self.get_metric_type(),
            {
                "ram_usage": ram_usage,
                "battery_info": battery_info
            }
        )

# Third Party Collector (UEFA Rankings)
class UEFACollector(CollectorInterface):
    def __init__(self):
        self.api_key = config.get("api.rapidapi.key")
        self.api_host = config.get("api.rapidapi.host")
        self.api_url = config.get("api.rapidapi.url")
        self.last_update = 0
        self.update_interval = 43200  # 12 hours in seconds

    def get_device_id(self) -> str:
        return "device_2"
    
    def get_metric_type(self) -> str:
        return "uefa_rankings"

    def collect(self) -> MetricData:
        """
        Collect UEFA rankings data from the API every 12 hours.
        Returns None if it's not time to update yet.
        """
        current_time = time.time()
        
        # Check if it's time to update (12 hours passed)
        if current_time - self.last_update < self.update_interval:
            return None

        try:
            headers = {
                "x-rapidapi-key": self.api_key,
                "x-rapidapi-host": self.api_host
            }
            response = requests.get(self.api_url, headers=headers)
            data = response.json()
            
            # Update the last update timestamp
            self.last_update = current_time
            
            # Return top 6 rankings
            return MetricData(
                self.get_device_id(),
                self.get_metric_type(),
                {
                    "rankings": data.get('rankings', [])[:6]
                }
            )
        except Exception as e:
            print(f"UEFA API Error: {e}")
            return None

# Uploader Queue
class UploaderQueue:
    def __init__(self):
        self.queue = []
        self._lock = threading.Lock()

    def add(self, data):
        with self._lock:
            self.queue.append(data)

    def get_all(self):
        with self._lock:
            data = self.queue.copy()
            self.queue.clear()
            return data

# Aggregator API
class MetricsAggregator:
    def __init__(self, database):
        self.database = database
        self.table_cache = set()
        self.init_db()

    def init_db(self):
        """
        Initialize the SQLite database with required tables.
        - uefa_rankings: Stores current UEFA club rankings
        - device_commands: Stores device commands and their execution status
        """
        conn = None
        try:
            conn = sqlite3.connect(self.database)
            cursor = conn.cursor()
            
            # Create UEFA rankings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS uefa_rankings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    club TEXT,               -- Name of the club
                    points REAL,             -- Current UEFA points
                    year INTEGER,            -- Year of the ranking
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP  -- Last update timestamp
                )
            ''')
            
            # Create device commands table for handling device operations
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS device_commands (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT NOT NULL,         -- Identifier of the target device
                    command TEXT NOT NULL,           -- Command to execute
                    status TEXT DEFAULT 'pending',   -- Command status (pending/completed/failed)
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,  -- When command was created
                    executed_at DATETIME,            -- When command was executed
                    response TEXT                    -- Command execution response
                )
            ''')
            
            conn.commit()
        except sqlite3.Error as e:
            print(f"Database initialization error: {e}")
        finally:
            if conn:
                conn.close()

    def get_table_name(self, device_id: str, metric_type: str) -> str:
        return f"metrics_{device_id}_{metric_type}"

    def ensure_table_exists(self, conn, table_name: str, metrics: dict):
        if table_name in self.table_cache:
            return

        cursor = conn.cursor()
        columns = [f"{key} REAL" for key in metrics.keys()]
        
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS {table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                {', '.join(columns)}
            )
        ''')
        
        self.table_cache.add(table_name)

    def save_metrics(self, metric_data: MetricData):
        """
        Save metrics to the database.
        For UEFA rankings, updates the uefa_rankings table with new data.
        """
        if not metric_data or not metric_data.values:
            return

        conn = None
        try:
            conn = sqlite3.connect(self.database)
            cursor = conn.cursor()

            # Handle UEFA rankings differently
            if metric_data.metric_type == "uefa_rankings":
                # Clear existing rankings
                cursor.execute("DELETE FROM uefa_rankings")
                
                # Insert new rankings
                current_year = time.strftime("%Y")
                for ranking in metric_data.values["rankings"]:
                    cursor.execute('''
                        INSERT INTO uefa_rankings (club, points, year)
                        VALUES (?, ?, ?)
                    ''', (ranking['team'], ranking['points'], current_year))

            conn.commit()
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()

# Collector Agent
class CollectorAgent:
    def __init__(self):
        self.collectors = []
        self.uploader_queue = UploaderQueue()
        self.aggregator = MetricsAggregator(config.get("database.path"))
        self.command_handlers = {
            'restart': self.handle_restart,
            'status': self.handle_status
        }

    def add_collector(self, collector):
        self.collectors.append(collector)

    def check_commands(self):
        """Check for pending commands for all collectors."""
        conn = None
        try:
            conn = sqlite3.connect(config.get("database.path"))
            cursor = conn.cursor()
            
            for collector in self.collectors:
                device_id = collector.get_device_id()
                cursor.execute('''
                    SELECT id, command 
                    FROM device_commands 
                    WHERE device_id = ? AND status = 'pending'
                    ORDER BY created_at
                ''', (device_id,))
                
                for cmd_id, command in cursor.fetchall():
                    try:
                        if command in self.command_handlers:
                            response = self.command_handlers[command](collector)
                            self.update_command_status(cmd_id, 'completed', response)
                        else:
                            self.update_command_status(cmd_id, 'failed', f'Unknown command: {command}')
                    except Exception as e:
                        self.update_command_status(cmd_id, 'failed', str(e))
                        
        except sqlite3.Error as e:
            print(f"Error checking commands: {e}")
        finally:
            if conn:
                conn.close()

    def update_command_status(self, cmd_id: int, status: str, response: str = None):
        """Update the status of a command."""
        conn = None
        try:
            conn = sqlite3.connect(config.get("database.path"))
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE device_commands 
                SET status = ?, response = ?, executed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (status, response, cmd_id))
            conn.commit()
        except sqlite3.Error as e:
            print(f"Error updating command status: {e}")
        finally:
            if conn:
                conn.close()

    def handle_restart(self, collector):
        """Handle restart command."""
        # Implement device-specific restart logic here
        return "Restart command executed"

    def handle_status(self, collector):
        """Handle status check command."""
        return "Device is running"

    def collect_and_upload(self):
        while True:
            for collector in self.collectors:
                data = collector.collect()
                if data:
                    self.uploader_queue.add(data)
            
            # Process queue
            metrics = self.uploader_queue.get_all()
            for metric in metrics:
                self.aggregator.save_metrics(metric)
            
            # Check for commands
            self.check_commands()
            
            time.sleep(300)  # 5 minutes interval

# Routes
@app.route('/metrics/<device_id>/<metric_type>')
def get_device_metrics(device_id, metric_type):
    conn = None
    try:
        conn = sqlite3.connect(config.get("database.path"))
        cursor = conn.cursor()
        table_name = f"metrics_{device_id}_{metric_type}"
        
        cursor.execute(f"SELECT * FROM {table_name} ORDER BY timestamp DESC LIMIT 1")
        row = cursor.fetchone()
        
        if row:
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [col[1] for col in cursor.fetchall()]
            return jsonify({
                "device_id": device_id,
                "metric_type": metric_type,
                "data": dict(zip(columns, row))
            })
            
        return jsonify({"error": "No data found"})
    except sqlite3.Error as e:
        return jsonify({"error": str(e)})
    finally:
        if conn:
            conn.close()

@app.route('/metrics')
def metrics():
    """Legacy endpoint to fetch system metrics."""
    return jsonify(get_system_metrics())

@app.route('/uefa-rankings')
def uefa_rankings():
    """Legacy endpoint to fetch UEFA club rankings."""
    conn = None
    try:
        conn = sqlite3.connect(config.get("database.path"))
        cursor = conn.cursor()
        cursor.execute('SELECT club, points FROM uefa_rankings ORDER BY points DESC')
        rankings = [{'rowName': row[0], 'points': row[1]} for row in cursor.fetchall()]
        return jsonify(rankings)
    except sqlite3.Error as e:
        return jsonify({"error": str(e)})
    finally:
        if conn:
            conn.close()

@app.route('/historical-rankings/<year>')
def historical_rankings_by_year(year):
    """Fetch historical rankings for a specific year."""
    try:
        with open('uefa_rankings.csv', 'r', encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)
            rankings = [
                {
                    'club': row['Club'],
                    'points': float(row['Points'])
                }
                for row in csv_reader
                if row['Year'] == year
            ]
            return jsonify(sorted(rankings, key=lambda x: x['points'], reverse=True))
    except Exception as e:
        print(f"Error: {e}")
        return jsonify([])

@app.route('/years')
def get_years():
    """Get available years for dropdown."""
    try:
        with open('uefa_rankings.csv', 'r', encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)
            years = sorted(set(row['Year'] for row in csv_reader), reverse=True)
            return jsonify(years)
    except Exception as e:
        print(f"Error reading years: {e}")
        return jsonify([])

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/device/command/<device_id>', methods=['POST'])
def send_command(device_id):
    """Send a command to a specific device."""
    command = request.json.get('command')
    if not command:
        return jsonify({"error": "Command is required"}), 400
        
    conn = None
    try:
        conn = sqlite3.connect(config.get("database.path"))
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO device_commands (device_id, command)
            VALUES (?, ?)
        ''', (device_id, command))
        conn.commit()
        return jsonify({
            "message": "Command sent successfully",
            "command_id": cursor.lastrowid
        })
    except sqlite3.Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/device/commands/<device_id>')
def get_device_commands(device_id):
    """Get command history for a device."""
    conn = None
    try:
        conn = sqlite3.connect(config.get("database.path"))
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, command, status, created_at, executed_at, response
            FROM device_commands
            WHERE device_id = ?
            ORDER BY created_at DESC
        ''', (device_id,))
        
        commands = []
        for row in cursor.fetchall():
            commands.append({
                "id": row[0],
                "command": row[1],
                "status": row[2],
                "created_at": row[3],
                "executed_at": row[4],
                "response": row[5]
            })
        return jsonify(commands)
    except sqlite3.Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

# Helper function for legacy support
def get_system_metrics():
    """Legacy function to fetch system metrics."""
    ram_usage = psutil.virtual_memory().percent
    battery = psutil.sensors_battery()
    battery_percent = battery.percent if battery else 0
    return {
        "ram": {"usage_percent": ram_usage},
        "battery": {"percent": battery_percent}
    }

if __name__ == "__main__":
    # Initialize collector agent
    agent = CollectorAgent()
    agent.add_collector(PCCollector())
    agent.add_collector(UEFACollector())
    
    # Start collection thread
    threading.Thread(target=agent.collect_and_upload, daemon=True).start()
    
    app.run(debug=True)