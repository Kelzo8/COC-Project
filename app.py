from flask import Flask, jsonify, render_template
import psutil
import threading
import requests
import sqlite3
import time
import csv
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST")
UEFA_RANKINGS_URL = "https://allsportsapi2.p.rapidapi.com/api/rankings/uefa/clubs"
DATABASE = os.getenv("DATABASE")
def init_db():
    """Initialize the database and create the tables if they don't exist."""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Keep existing table for live API data
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS uefa_rankings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                club TEXT,
                points REAL,
                year INTEGER
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ram_usage REAL,
                battery_level REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        if conn:
            conn.close()

def save_uefa_rankings(rankings):
    """Save UEFA rankings to the database."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE, timeout=20)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM uefa_rankings')  # Clear existing data
        for ranking in rankings:
            cursor.execute('''
                INSERT INTO uefa_rankings (club, points)
                VALUES (?, ?)
            ''', (ranking['rowName'], ranking['points']))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

def get_system_metrics():
    """Fetch system metrics."""
    ram_usage = psutil.virtual_memory().percent
    battery = psutil.sensors_battery()
    battery_percent = battery.percent if battery else 0
    return {
        "ram": {"usage_percent": ram_usage},
        "battery": {"percent": battery_percent}
    }

def get_uefa_rankings():
    """Fetch UEFA club rankings."""
    try:
        headers = {
            "x-rapidapi-key": RAPIDAPI_KEY,
            "x-rapidapi-host": RAPIDAPI_HOST
        }
        response = requests.get(UEFA_RANKINGS_URL, headers=headers)
        data = response.json()
        rankings = data.get('rankings', [])[:6]  # Return only the top 6 rankings
        return rankings
    except Exception as e:
        print("Error fetching UEFA rankings:", str(e))
        return {"error": str(e)}

def fetch_and_save_uefa_rankings_periodically():
    """Fetch and save UEFA rankings to the database every 3 days."""
    while True:
        rankings = get_uefa_rankings()
        if 'error' not in rankings:
            save_uefa_rankings(rankings)
        time.sleep(3 * 24 * 60 * 60)  # Sleep for 3 days

def save_metrics_to_db(ram_usage, battery_level):
    """Save system metrics to the database."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO system_metrics (ram_usage, battery_level)
            VALUES (?, ?)
        ''', (ram_usage, battery_level))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error saving metrics: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

def metrics_logger():
    """Log system metrics to database every 5 minutes."""
    while True:
        try:
            ram = psutil.virtual_memory().percent
            battery = psutil.sensors_battery()
            battery_level = battery.percent if battery else 0
            save_metrics_to_db(ram, battery_level)
            print(f"Metrics saved: RAM {ram}%, Battery {battery_level}%")
        except Exception as e:
            print(f"Error logging metrics: {e}")
        time.sleep(300)  # Wait 5 minutes

@app.route('/metrics')
def metrics():
    """Endpoint to fetch system metrics."""
    return jsonify(get_system_metrics())

@app.route('/uefa-rankings')
def uefa_rankings():
    """Endpoint to fetch UEFA club rankings."""
    return jsonify(get_uefa_rankings())

@app.route('/historical-rankings')
def historical_rankings():
    """Endpoint to fetch historical UEFA club rankings."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE, timeout=20)  # Add timeout parameter
        cursor = conn.cursor()
        cursor.execute('''
            SELECT club_id, club_name, points, year 
            FROM uefa_historical_rankings 
            ORDER BY year DESC, points DESC
        ''')
        rankings = cursor.fetchall()
        
        formatted_rankings = [
            {
                'club_id': rank[0],
                'club_name': rank[1],
                'points': rank[2],
                'year': rank[3]
            } for rank in rankings
        ]
        
        return jsonify(formatted_rankings)
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return jsonify({"error": "Database error occurred"}), 500
    finally:
        if conn:
            conn.close()

@app.route('/')
def index():
    """Render the main dashboard page."""
    return render_template('index.html')

def insert_historical_data():
    """Insert historical UEFA rankings data from CSV file."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Clear existing data
        cursor.execute('DELETE FROM uefa_historical_rankings')
        
        # Read data from CSV file
        with open('uefa_rankings.csv', 'r', encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)
            data = [
                (
                    index + 1,  # Generate club_id automatically
                    row['club'],
                    float(row['points']),
                    int(row['year'])
                )
                for index, row in enumerate(csv_reader)
            ]
        
        cursor.executemany('''
            INSERT INTO uefa_historical_rankings (club_id, club_name, points, year)
            VALUES (?, ?, ?, ?)
        ''', data)
        
        conn.commit()
        print("Historical data inserted successfully!")
    except Exception as e:
        print(f"Error: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

@app.route('/years')
def get_years():
    """Get available years for dropdown."""
    try:
        with open('uefa_rankings.csv', 'r', encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)
            years = sorted(set(row['Year'] for row in csv_reader), reverse=True)  # Note the capital 'Y' in 'Year'
            print(f"Available years: {years}")
            return jsonify(years)
    except Exception as e:
        print(f"Error reading years: {e}")
        return jsonify([])

@app.route('/historical-rankings/<year>')
def historical_rankings_by_year(year):
    """Fetch historical rankings for a specific year."""
    try:
        with open('uefa_rankings.csv', 'r', encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)
            rankings = [
                {
                    'club': row['Club'],
                    'points': float(row['Points'])
                }
                for row in csv_reader
                if row['Year'] == year
            ]
            return jsonify(sorted(rankings, key=lambda x: x['points'], reverse=True))
    except Exception as e:
        print(f"Error: {e}")
        return jsonify([])

if __name__ == "__main__":
    init_db()
    threading.Thread(target=fetch_and_save_uefa_rankings_periodically, daemon=True).start()
    threading.Thread(target=metrics_logger, daemon=True).start()
    app.run(debug=True)