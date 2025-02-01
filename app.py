from flask import Flask, jsonify, render_template
import psutil
import threading
import requests

app = Flask(__name__)

API_KEY = "0eef57aafc7b2aaeaf8b45248de809ea"  # Replace with your actual API key from The Odds API
ODDS_API_URL = "https://api.the-odds-api.com/v4/sports/upcoming/odds"  # Adjusted to use upcoming sports odds

def get_ram_usage():
    """Fetch system RAM usage metrics."""
    ram = psutil.virtual_memory()
    return {
        'total_gb': round(ram.total / (1024 ** 3), 2),
        'available_gb': round(ram.available / (1024 ** 3), 2),
        'used_gb': round(ram.used / (1024 ** 3), 2),
        'usage_percent': ram.percent
    }

def get_thread_count():
    """Fetch the number of active threads."""
    return threading.active_count()

def get_betting_odds():
    """Fetch and parse betting odds from the API."""
    try:
        params = {
            "api_key": API_KEY,
            "regions": "us",  # Odds from US-based bookmakers
            "markets": "h2h,spreads",  # Head-to-head and spread markets
            "oddsFormat": "decimal",  # Decimal odds format
            "dateFormat": "iso",  # ISO date format
        }
        response = requests.get(ODDS_API_URL, params=params)
        data = response.json()

        # Debugging: Print API response
        print("API Response:", data)

        odds_list = []
        if isinstance(data, list):
            for event in data:
                event_name = event.get("sport_title", "Unknown Event")
                if event_name in ["EPL", "Championship"]:
                    bookmakers = event.get("bookmakers", [])
                    if bookmakers:
                        markets = bookmakers[0].get("markets", [])
                        if markets:
                            outcomes = markets[0].get("outcomes", [])
                            if outcomes:
                                favorite = min(outcomes, key=lambda x: x["price"])
                                odds_list.append({
                                    "event": event_name,
                                    "team": favorite["name"],
                                    "odds": favorite["price"]
                                })

        return odds_list
    except Exception as e:
        print("Error fetching odds:", str(e))  # Debugging
        return {"error": str(e)}

@app.route('/metrics')
def metrics():
    """Endpoint to fetch system metrics."""
    try:
        return jsonify({
            'ram': get_ram_usage(),
            'threads': get_thread_count()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/odds')
def odds():
    """Endpoint to fetch betting odds."""
    return jsonify(get_betting_odds())

@app.route('/')
def index():
    """Render the dashboard."""
    return render_template('index.html')

if __name__ == "__main__":
    app.run(debug=True)
