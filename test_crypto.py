from src.services.crypto_collector import CryptoCollector
from src.services.collector_agent import CollectorAgent
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_crypto_collection():
    # Create collector and agent
    crypto_collector = CryptoCollector()
    agent = CollectorAgent()
    
    # Add collector to agent
    agent.add_collector(crypto_collector)
    
    # Run one collection cycle
    metrics_data = agent._collect_all_metrics()
    logger.info(f"Collected metrics: {metrics_data}")
    
    # Send to server
    agent._send_to_server(metrics_data)

if __name__ == "__main__":
    test_crypto_collection() 