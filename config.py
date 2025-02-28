import json
import os
from typing import Dict, Any

class Config:
    _instance = None
    _config: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance

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

    def get(self, key_path: str, default=None) -> Any:
        keys = key_path.split('.')
        value = self._config
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key, default)
            else:
                return default
        return value 