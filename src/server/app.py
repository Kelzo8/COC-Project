import os
import logging
from flask import Flask, jsonify
from .routes import MetricsAPI
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from .models import Base  # Make sure this imports your SQLAlchemy models

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app():
    app = Flask(__name__, template_folder='../../templates')
    
    # Use PostgreSQL database URL from environment or fallback to the Render external URL
    database_url = os.getenv('DATABASE_URL', 
        'postgresql://kelzodb_user:b9WCxmKsbZSTq0EYqGJ6aM0wU7Nl4ege@dpg-cv5cv77noe9s73egtus0-a.oregon-postgres.render.com/kelzodb'
    )
    
    try:
        # Initialize database
        engine = create_engine(database_url)
        SessionLocal = sessionmaker(bind=engine)
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        
        # Initialize metrics API with database configuration
        metrics_api = MetricsAPI(database_url)
        metrics_api.init_routes(app)
        
        # Add error handlers
        @app.errorhandler(404)
        def not_found_error(error):
            return jsonify({'error': 'Resource not found'}), 404

        @app.errorhandler(500)
        def internal_error(error):
            return jsonify({'error': 'Internal server error'}), 500
            
        return app
        
    except SQLAlchemyError as e:
        logger.error(f"Database initialization error: {str(e)}")
        raise

app = create_app()

if __name__ == "__main__":
    # Get port from environment variable for Render
    port = int(os.getenv('PORT', 10000))
    app.run(host='0.0.0.0', port=port) 