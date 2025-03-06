import os
from src.server.app import create_app
from src.services.collector_agent import CollectorAgent
from src.services.pc_collector import PCCollector
from src.services.crypto_collector import CryptoCollector
import threading

app = create_app()

def start_collector():
    """Initialize and start the collector agent"""
    # Get server URL from environment variable or use default
    server_url = os.getenv('SERVER_URL', 'http://localhost:5000')
    
    agent = CollectorAgent(server_url)
    agent.add_collector(PCCollector())
    agent.add_collector(CryptoCollector())
    
    # Start collection thread
    threading.Thread(target=agent.collect_and_upload, daemon=True).start()
    
if __name__ == "__main__":
    # Only start collector if running locally
    if os.getenv('ENVIRONMENT') != 'production':
        start_collector()
    
    # Get port from environment variable for production
    port = int(os.getenv('PORT', 5000))
    
    app.run(
        host='0.0.0.0',  # Make accessible from outside
        port=port,
        debug=os.getenv('ENVIRONMENT') != 'production'
    )