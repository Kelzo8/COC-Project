import json
import os
from typing import Dict, Any
from dotenv import load_dotenv

DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///instance/uefa_rankings.db')

class Config:
    _instance = None
    _config: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def __init__(self):
        load_dotenv()  # Load environment variables from .env file
        
        # Required configurations
        self.required_configs = {
            "api.rapidapi.key": os.getenv('RAPIDAPI_KEY'),
            "database.path": "instance/metrics.db"
        }
        
        # Validate required configurations
        missing_configs = [
            key for key, value in self.required_configs.items() 
            if not value
        ]
        
        if missing_configs:
            raise ValueError(
                f"Missing required configurations: {', '.join(missing_configs)}"
            )

    def _load_config(self):
        config_path = os.path.join(os.path.dirname(__file__), 'config.json')
        with open(config_path, 'r') as f:
            self._config = json.load(f)

        # Override with environment variables if they exist
        if os.getenv("RAPIDAPI_KEY"):
            self._config["api"]["rapidapi"]["key"] = os.getenv("RAPIDAPI_KEY")
        if os.getenv("RAPIDAPI_HOST"):
            self._config["api"]["rapidapi"]["host"] = os.getenv("RAPIDAPI_HOST")
        if os.getenv("DATABASE"):
            self._config["database"]["path"] = os.getenv("DATABASE")

    def get(self, key):
        return self.required_configs.get(key)