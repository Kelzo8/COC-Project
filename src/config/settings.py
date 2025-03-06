import os
from pathlib import Path

class Settings:
    def __init__(self):
        self.ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
        
        # Database settings
        if self.ENVIRONMENT == 'production':
            self.DATABASE_URL = os.getenv('DATABASE_URL')
            # Handle Render's Postgres URL format if needed
            if self.DATABASE_URL and self.DATABASE_URL.startswith('postgres://'):
                self.DATABASE_URL = self.DATABASE_URL.replace('postgres://', 'postgresql://', 1)
        else:
            db_path = Path(__file__).parent.parent.parent / 'instance' / 'metrics.db'
            self.DATABASE_URL = f"sqlite:///{db_path}"

        # Server settings
        self.SERVER_URL = os.getenv('SERVER_URL', 'http://localhost:5000')
        self.PORT = int(os.getenv('PORT', 5000))
        
        # API settings
        self.API_RAPIDAPI_KEY = os.getenv('API_RAPIDAPI_KEY')
        self.API_RAPIDAPI_HOST = os.getenv('API_RAPIDAPI_HOST')
        self.API_RAPIDAPI_URL = os.getenv('API_RAPIDAPI_URL')

settings = Settings() 