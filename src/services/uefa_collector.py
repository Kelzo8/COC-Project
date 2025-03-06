import time
import requests
from ..models.collector import CollectorInterface
from ..models.metric_data import MetricData
from config import Config
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UEFACollector(CollectorInterface):
    def __init__(self):
        self.api_key = "da62be9e24msheae0f8d203fa470p1f013ejsn172018fb6771"
        self.api_host = "allsportsapi2.p.rapidapi.com"
        self.api_url = "https://allsportsapi2.p.rapidapi.com/api/rankings/fifa"
        self.last_update = 0
        self.update_interval = 3600  # 1 hour
        
        logger.info("FIFA Rankings Collector initialized")

    def get_device_id(self) -> str:
        return "device_2"
    
    def get_metric_type(self) -> str:
        return "uefa_rankings"

    def collect(self) -> MetricData:
        """Collect FIFA rankings"""
        current_time = time.time()
        
        # Check if it's time to update
        if current_time - self.last_update < self.update_interval:
            logger.info("Not time to update FIFA rankings yet")
            return None

        try:
            logger.info("Fetching FIFA rankings")
            
            headers = {
                "x-rapidapi-key": self.api_key,
                "x-rapidapi-host": self.api_host
            }
            
            response = requests.get(
                self.api_url, 
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            logger.info("FIFA rankings data received")
            
            # Process the rankings data
            rankings = []
            try:
                # Extract top 6 teams from the response
                for team in data[:6]:
                    rankings.append({
                        "team": team['name'],
                        "points": float(team['points'])
                    })
            except (KeyError, TypeError) as e:
                logger.error(f"Error processing rankings data: {e}")
                logger.debug(f"Raw data received: {data}")
                return None

            if not rankings:
                logger.warning("No rankings data processed")
                return None

            logger.info(f"Processed rankings: {rankings}")
            
            # Update the last update timestamp
            self.last_update = current_time
            
            # Create and return MetricData object
            return MetricData(
                device_id=self.get_device_id(),
                metric_type=self.get_metric_type(),
                values={"rankings": rankings}
            )
            
        except requests.exceptions.RequestException as e:
            logger.error(f"FIFA API Request Error: {e}")
            return None
        except Exception as e:
            logger.error(f"FIFA Data Processing Error: {e}", exc_info=True)
            return None 