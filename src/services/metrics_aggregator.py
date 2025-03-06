from datetime import datetime
import time
from ..models.metric_data import MetricData
from ..server.database import Database, UEFARanking
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MetricsAggregator:
    def __init__(self, database_path):
        database_url = f"sqlite:///{database_path}"
        self.db = Database(database_url)
        self.session = self.db.get_session()

    def get_table_name(self, device_id: str, metric_type: str) -> str:
        return f"metrics_{device_id}_{metric_type}"

    def save_metrics(self, metric_data: MetricData):
        """Save metrics to the database using SQLAlchemy ORM"""
        if not metric_data or not metric_data.values:
            return

        try:
            # Handle UEFA rankings
            if metric_data.metric_type == "uefa_rankings":
                # Clear existing rankings
                self.session.query(UEFARanking).delete()
                
                # Insert new rankings
                current_year = int(time.strftime("%Y"))
                for ranking in metric_data.values["rankings"]:
                    new_ranking = UEFARanking(
                        club=ranking['team'],
                        points=ranking['points'],
                        year=current_year
                    )
                    self.session.add(new_ranking)
            else:
                # Handle dynamic metric tables
                table_name = self.get_table_name(
                    metric_data.device_id,
                    metric_data.metric_type
                )
                MetricModel = self.db.create_metric_table(table_name, metric_data.values)
                
                # Create new metric record
                new_metric = MetricModel(**metric_data.values)
                self.session.add(new_metric)

            self.session.commit()
        except Exception as e:
            print(f"Database error: {e}")
            self.session.rollback()
            raise

    def _handle_uefa_rankings(self, data):
        """Handle UEFA rankings data"""
        table_name = f"metrics_{data['device_id']}_{data['metric_type']}"
        
        # Create table if it doesn't exist
        MetricModel = self.db.create_metric_table(table_name, {
            "rankings": "TEXT"  # Store rankings as JSON string
        })
        
        # Create new metric record
        new_metric = MetricModel(
            rankings=json.dumps(data['values']['rankings'])
        )
        
        # Set timestamp if provided
        if 'timestamp' in data:
            new_metric.timestamp = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
        
        self.session.add(new_metric)
        self.session.commit()
        logger.info(f"Saved UEFA rankings: {data['values']['rankings']}") 