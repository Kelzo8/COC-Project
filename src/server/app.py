import os
from flask import Flask
from .routes import MetricsAPI

def create_app():
    app = Flask(__name__, template_folder='../../templates')
    
    # Use PostgreSQL database URL from environment or fallback to the Render external URL
    database_url = os.getenv('DATABASE_URL', 
        'postgresql://kelzodb_user:b9WCxmKsbZSTq0EYqGJ6aM0wU7Nl4ege@dpg-cv5cv77noe9s73egtus0-a.oregon-postgres.render.com/kelzodb'
    )
    
    # Initialize metrics API with database configuration
    metrics_api = MetricsAPI(database_url)
    metrics_api.init_routes(app)

    return app

app = create_app()

if __name__ == "__main__":
    # Get port from environment variable for Render
    port = int(os.getenv('PORT', 10000))
    app.run(host='0.0.0.0', port=port) 