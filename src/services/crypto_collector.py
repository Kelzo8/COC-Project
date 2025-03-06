import time
import requests
from ..models.collector import CollectorInterface
from ..models.metric_data import MetricData
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CryptoCollector(CollectorInterface):
    def __init__(self):
        self.api_url = "https://api.coingecko.com/api/v3/simple/price"
        self.last_update = 0
        self.update_interval = 300  # 5 minutes
        
        logger.info("Crypto Collector initialized")

    def get_device_id(self) -> str:
        return "device_3"
    
    def get_metric_type(self) -> str:
        return "crypto_prices"

    def collect(self) -> MetricData:
        """Collect Bitcoin and Ethereum prices"""
        current_time = time.time()
        
        # Check if it's time to update
        if current_time - self.last_update < self.update_interval:
            logger.info("Not time to update crypto prices yet")
            return None

        try:
            logger.info("Fetching crypto prices")
            
            params = {
                "ids": "bitcoin,ethereum",
                "vs_currencies": "usd"
            }
            
            response = requests.get(
                self.api_url,
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            logger.info("Crypto price data received")
            
            # Format the prices data to match frontend expectations
            prices = {
                "bitcoin_usd": data['bitcoin']['usd'],
                "ethereum_usd": data['ethereum']['usd']
            }
            
            logger.info(f"Processed prices: {prices}")
            
            # Update the last update timestamp
            self.last_update = current_time
            
            return MetricData(
                device_id=self.get_device_id(),
                metric_type=self.get_metric_type(),
                values=prices
            )
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Crypto API Request Error: {e}")
            return None
        except Exception as e:
            logger.error(f"Crypto Data Processing Error: {e}", exc_info=True)
            return None 