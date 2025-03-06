import threading
import time
import requests
from datetime import datetime
from urllib.parse import urljoin
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CollectorAgent:
    def __init__(self, base_url=None):
        self.collectors = []
        self.base_url = base_url or os.getenv('SERVER_URL', 'http://localhost:5000')
        logger.info(f"CollectorAgent initialized with base_url: {self.base_url}")

    def add_collector(self, collector):
        self.collectors.append(collector)

    def collect_and_upload(self):
        while True:
            try:
                metrics_data = self._collect_all_metrics()
                if metrics_data and metrics_data["metrics"]:  # Check if we have any metrics
                    self._send_to_server(metrics_data)
            except Exception as e:
                logger.error(f"Error in collection cycle: {e}", exc_info=True)
            
            time.sleep(300)  # 5 minutes interval

    def _collect_all_metrics(self):
        """Collect metrics from all collectors"""
        metrics_collection = {
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "metrics": []
        }

        for collector in self.collectors:
            try:
                metric_data = collector.collect()
                if metric_data and hasattr(metric_data, 'device_id'):  # Verify we have valid MetricData
                    metrics_collection["metrics"].append({
                        "device_id": metric_data.device_id,
                        "metric_type": metric_data.metric_type,
                        "values": metric_data.values
                    })
                    logger.info(f"Collected {metric_data.metric_type} from {metric_data.device_id}")
            except Exception as e:
                logger.error(f"Error collecting from {collector.__class__.__name__}: {e}")

        return metrics_collection

    def _send_to_server(self, metrics_data):
        """Send metrics to server endpoint"""
        try:
            endpoint = urljoin(self.base_url, "/metrics/snapshot")
            logger.info(f"Sending metrics batch to {endpoint}: {metrics_data}")
            
            response = requests.post(
                endpoint,
                json=metrics_data,
                timeout=10
            )
            response.raise_for_status()
            logger.info(f"Server response: {response.status_code} - {response.text}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending metrics to server: {e}") 