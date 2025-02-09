from flask import Flask, jsonify, render_template
import psutil
import threading
import requests
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///uefa_rankings.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

RAPIDAPI_KEY = "da62be9e24msheae0f8d203fa470p1f013ejsn172018fb6771"
RAPIDAPI_HOST = "allsportsapi2.p.rapidapi.com"
UEFA_RANKINGS_URL = "https://allsportsapi2.p.rapidapi.com/api/rankings/uefa/clubs"

class UefaRanking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    position = db.Column(db.Integer, nullable=False)
    team_name = db.Column(db.String(100), nullable=False)
    points = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<UefaRanking {self.team_name} - {self.points}>'

def get_system_metrics():
    """Fetch system metrics."""
    ram_usage = psutil.virtual_memory().percent
    threads = threading.active_count()
    return {"ram": {"usage_percent": ram_usage}, "threads": threads}

def fetch_uefa_rankings():
    """Fetch UEFA club rankings from the API."""
    try:
        headers = {
            "x-rapidapi-key": RAPIDAPI_KEY,
            "x-rapidapi-host": RAPIDAPI_HOST
        }
        response = requests.get(UEFA_RANKINGS_URL, headers=headers)
        data = response.json()
        return data.get('rankings', [])[:6]  # Return only the top 6 rankings
    except Exception as e:
        print("Error fetching UEFA rankings:", str(e))
        return []

def save_uefa_rankings(rankings):
    """Save UEFA rankings to the database."""
    for ranking in rankings:
        new_ranking = UefaRanking(
            position=ranking['ranking'],
            team_name=ranking['rowName'],
            points=ranking['points']
        )
        db.session.add(new_ranking)
    db.session.commit()

def scheduled_task():
    """Scheduled task to fetch and save UEFA rankings."""
    rankings = fetch_uefa_rankings()
    save_uefa_rankings(rankings)

scheduler = BackgroundScheduler()
scheduler.add_job(scheduled_task, 'interval', hours=24)
scheduler.start()

@app.route('/metrics')
def metrics():
    """Endpoint to fetch system metrics."""
    return jsonify(get_system_metrics())

@app.route('/uefa-rankings')
def uefa_rankings():
    """Endpoint to fetch and save UEFA club rankings."""
    rankings = fetch_uefa_rankings()
    save_uefa_rankings(rankings)
    return jsonify(rankings)

@app.route('/uefa-rankings/history')
def uefa_rankings_history():
    """Endpoint to fetch UEFA club rankings history."""
    history = UefaRanking.query.order_by(UefaRanking.timestamp.desc()).all()
    return jsonify([{
        'position': ranking.position,
        'team_name': ranking.team_name,
        'points': ranking.points,
        'timestamp': ranking.timestamp
    } for ranking in history])

@app.route('/')
def index():
    """Render the main dashboard page."""
    return render_template('index.html')

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)