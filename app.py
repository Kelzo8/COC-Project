from flask import Flask, jsonify, render_template
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
class CollectorInterface(ABC):
    @abstractmethod
    def collect(self):
        pass

# PC Metrics Collector
class PCCollector(CollectorInterface):
    def collect(self):
        ram_usage = psutil.virtual_memory().percent
        battery = psutil.sensors_battery()
        battery_percent = battery.percent if battery else 0
        return {
            "device_id": "device_1",
            "metrics": {
                "ram_usage": ram_usage,
                "battery_level": battery_percent
            }
        }

# Third Party Collector (UEFA Rankings)
class UEFACollector(CollectorInterface):
    def __init__(self):
        self.api_key = config.get("api.rapidapi.key")
        self.api_host = config.get("api.rapidapi.host")
        self.api_url = config.get("api.uefa_rankings_url")

    def collect(self):
        try:
            headers = {
                "x-rapidapi-key": self.api_key,
                "x-rapidapi-host": self.api_host
            }
            response = requests.get(self.api_url, headers=headers)
            data = response.json()
            return {
                "device_id": "device_2",
                "metrics": {
                    "rankings": data.get('rankings', [])[:6]
                }
            }
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
        self.init_db()

    def init_db(self):
        """Initialize the database with legacy tables."""
        conn = None
        try:
            conn = sqlite3.connect(self.database)
            cursor = conn.cursor()
            
            # Create legacy tables
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS uefa_rankings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    club TEXT,
                    points REAL,
                    year INTEGER
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS uefa_historical_rankings (
                    club_id INTEGER PRIMARY KEY,
                    club_name TEXT,
                    points REAL,
                    year INTEGER
                )
            ''')
            
            conn.commit()
        except sqlite3.Error as e:
            print(f"Database initialization error: {e}")
        finally:
            if conn:
                conn.close()

    def save_metrics(self, data):
        conn = None
        try:
            conn = sqlite3.connect(self.database)
            cursor = conn.cursor()
            
            device_id = data['device_id']
            metrics = data['metrics']
            
            # Create device-specific table if not exists
            columns = [f"{key} REAL" for key in metrics.keys()]
            table_name = f"metrics_{device_id}"
            
            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {table_name} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    {', '.join(columns)}
                )
            ''')
            
            # Insert metrics
            columns = list(metrics.keys())
            values = [metrics[col] for col in columns]
            placeholders = ','.join(['?' for _ in values])
            
            cursor.execute(f'''
                INSERT INTO {table_name} ({','.join(columns)})
                VALUES ({placeholders})
            ''', values)
            
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

    def add_collector(self, collector):
        self.collectors.append(collector)

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
            
            time.sleep(300)  # 5 minutes interval

# Routes
@app.route('/metrics/<device_id>')
def get_device_metrics(device_id):
    conn = None
    try:
        conn = sqlite3.connect(config.get("database.path"))
        cursor = conn.cursor()
        table_name = f"metrics_{device_id}"
        cursor.execute(f"SELECT * FROM {table_name} ORDER BY timestamp DESC LIMIT 1")
        row = cursor.fetchone()
        if row:
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [col[1] for col in cursor.fetchall()]
            return jsonify(dict(zip(columns, row)))
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