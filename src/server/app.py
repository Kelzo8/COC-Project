from flask import Flask
from ..config.settings import settings
from .routes import MetricsAPI

def create_app():
    app = Flask(__name__, template_folder='../../templates')
    
    # Configure app based on environment
    app.config['ENV'] = settings.ENVIRONMENT
    app.config['DEBUG'] = settings.ENVIRONMENT != 'production'
    
    # Initialize metrics API with database configuration
    metrics_api = MetricsAPI(settings.DATABASE_URL)
    metrics_api.init_routes(app)

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True) 