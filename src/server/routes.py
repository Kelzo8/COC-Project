import csv
import sqlite3
from flask import jsonify, render_template, request
from config import Config
from .database import Database, UEFARanking
from datetime import datetime, timedelta
import time
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MetricsAPI:
    def __init__(self, database_url):
        self.db = Database(database_url)
        self.session = self.db.get_session()
        logger.info(f"MetricsAPI initialized with database_url: {database_url}")

    def init_routes(self, app):
        @app.route('/metrics/snapshot', methods=['POST'])
        def save_metrics_snapshot():
            """
            Endpoint to receive and store metrics snapshots
            Expected format:
            {
                "device_id": "device_1",
                "metric_type": "system_metrics",
                "values": {
                    "ram_usage": 45.2,
                    "thread_count": 8
                },
                "timestamp": "2024-03-05T12:00:00Z"
            }
            """
            data = request.json
            logger.info(f"Received metrics snapshot: {data}")

            if not self._validate_metrics_data(data):
                logger.error(f"Invalid metrics data format: {data}")
                return jsonify({"error": "Invalid metrics data format"}), 400

            try:
                if data['metric_type'] == "uefa_rankings":
                    self._handle_uefa_rankings(data['values'])
                else:
                    self._handle_generic_metrics(data)
                
                logger.info("Metrics saved successfully")
                return jsonify({"message": "Metrics saved successfully"}), 200
            except Exception as e:
                logger.error(f"Error saving metrics: {e}")
                return jsonify({"error": str(e)}), 500

        @app.route('/metrics/<device_id>/<metric_type>')
        def get_device_metrics(device_id, metric_type):
            logger.info(f"Fetching metrics for device {device_id}, type {metric_type}")
            try:
                table_name = f"metrics_{device_id}_{metric_type}"
                MetricModel = self.db.get_metric_table(table_name)
                
                if not MetricModel:
                    logger.warning(f"No metric table found for {table_name}")
                    return jsonify({"error": "No metrics found"}), 404
                
                latest_metric = (self.session.query(MetricModel)
                               .order_by(MetricModel.timestamp.desc())
                               .first())
                
                if latest_metric:
                    # Convert SQLAlchemy model to dict
                    metric_dict = {}
                    for column in MetricModel.__table__.columns:
                        if column.name != 'id':
                            value = getattr(latest_metric, column.name)
                            if isinstance(value, datetime):
                                value = value.isoformat() + 'Z'
                            metric_dict[column.name] = value

                    response_data = {
                        "device_id": device_id,
                        "metric_type": metric_type,
                        "data": metric_dict
                    }
                    logger.info(f"Returning metrics data: {response_data}")
                    return jsonify(response_data)
                
                logger.warning("No data found in table")
                return jsonify({"error": "No data found"}), 404
            except Exception as e:
                logger.error(f"Error fetching metrics: {e}", exc_info=True)
                return jsonify({"error": str(e)}), 500

        @app.route('/uefa-rankings')
        def uefa_rankings():
            """Legacy endpoint to fetch UEFA club rankings."""
            try:
                rankings = (self.session.query(UEFARanking)
                          .order_by(UEFARanking.points.desc())
                          .all())
                
                return jsonify([{
                    'rowName': ranking.club,
                    'points': ranking.points
                } for ranking in rankings])
            except Exception as e:
                return jsonify({"error": str(e)}), 500

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
                config = Config()
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
                config = Config()
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

        @app.route('/debug/metrics')
        def debug_metrics():
            """Debug endpoint to view latest metrics"""
            if not app.debug:
                return jsonify({"error": "Debug mode not enabled"}), 403
            
            try:
                data = {}
                # Get system metrics
                system_metrics = self.session.query(
                    self.db.get_metric_table("metrics_device_1_system_metrics")
                ).order_by("timestamp desc").first()
                
                if system_metrics:
                    data["system_metrics"] = {
                        column.name: getattr(system_metrics, column.name)
                        for column in system_metrics.__table__.columns
                    }
                    
                # Get UEFA rankings
                uefa_metrics = self.session.query(
                    self.db.get_metric_table("metrics_device_2_uefa_rankings")
                ).order_by("timestamp desc").first()
                
                if uefa_metrics:
                    data["uefa_rankings"] = {
                        column.name: getattr(uefa_metrics, column.name)
                        for column in uefa_metrics.__table__.columns
                    }
                    
                return jsonify(data)
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @app.route('/metrics/history/<device_id>/<metric_type>')
        def get_metrics_history(device_id, metric_type):
            """Get historical metrics data with time range filtering"""
            try:
                # Get time range from query parameters (default to last 24 hours)
                time_range = request.args.get('range', '24h')
                
                # Calculate time range
                end_time = datetime.utcnow()
                if time_range == '24h':
                    start_time = end_time - timedelta(days=1)
                elif time_range == '7d':
                    start_time = end_time - timedelta(days=7)
                elif time_range == '30d':
                    start_time = end_time - timedelta(days=30)
                else:
                    start_time = end_time - timedelta(days=1)  # Default to 24h

                # Get table and query data
                table_name = f"metrics_{device_id}_{metric_type}"
                MetricModel = self.db.get_metric_table(table_name)
                
                if not MetricModel:
                    return jsonify({"error": "No metrics found"}), 404
                
                # Query data within time range
                metrics = (self.session.query(MetricModel)
                          .filter(MetricModel.timestamp.between(start_time, end_time))
                          .order_by(MetricModel.timestamp.asc())
                          .all())
                
                # Format response based on metric type
                if metric_type == 'system_metrics':
                    data = [{
                        'timestamp': m.timestamp.isoformat(),
                        'ram_usage': m.ram_usage,
                        'thread_count': m.thread_count
                    } for m in metrics]
                elif metric_type == 'crypto_prices':
                    data = [{
                        'timestamp': m.timestamp.isoformat(),
                        'bitcoin_usd': m.bitcoin_usd,
                        'ethereum_usd': m.ethereum_usd
                    } for m in metrics]
                elif metric_type == 'uefa_rankings':
                    data = [{
                        'timestamp': m.timestamp.isoformat(),
                        'rankings': json.loads(m.rankings)
                    } for m in metrics]
                
                return jsonify({
                    'device_id': device_id,
                    'metric_type': metric_type,
                    'time_range': time_range,
                    'data': data
                })

            except Exception as e:
                logger.error(f"Error fetching historical metrics: {e}", exc_info=True)
                return jsonify({"error": str(e)}), 500

    def _validate_metrics_data(self, data):
        """Validate incoming metrics data"""
        required_fields = ['device_id', 'metric_type', 'values']
        return all(field in data for field in required_fields)

    def _handle_uefa_rankings(self, rankings_data):
        """Handle UEFA rankings data"""
        # Clear existing rankings
        self.session.query(UEFARanking).delete()
        
        # Insert new rankings
        current_year = int(time.strftime("%Y"))
        for ranking in rankings_data["rankings"]:
            new_ranking = UEFARanking(
                club=ranking['team'],
                points=ranking['points'],
                year=current_year
            )
            self.session.add(new_ranking)
        
        self.session.commit()

    def _handle_generic_metrics(self, data):
        """Handle generic metrics data"""
        table_name = f"metrics_{data['device_id']}_{data['metric_type']}"
        MetricModel = self.db.create_metric_table(table_name, data['values'])
        
        # Create new metric record with all values
        new_metric = MetricModel(**data['values'])
        
        # Set timestamp if provided
        if 'timestamp' in data:
            new_metric.timestamp = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
        
        self.session.add(new_metric)
        self.session.commit()
        logger.info(f"Saved generic metrics to {table_name}: {data['values']}")

def get_system_metrics():
    """Legacy function to fetch system metrics."""
    import psutil
    import threading
    ram_usage = psutil.virtual_memory().percent
    thread_count = threading.active_count()
    return {
        "ram": {"usage_percent": ram_usage},
        "threads": {"count": thread_count}
    } 