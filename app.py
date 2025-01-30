from flask import Flask, jsonify, render_template
import psutil
import threading
import time

app = Flask(__name__)

def get_ram_usage():
    ram = psutil.virtual_memory()
    ram_metrics = {
        'total_gb': round(ram.total / (1024 ** 3), 2),
        'available_gb': round(ram.available / (1024 ** 3), 2),
        'used_gb': round(ram.used / (1024 ** 3), 2),
        'usage_percent': ram.percent
    }
    return ram_metrics

def get_thread_count():
    return threading.active_count()

@app.route('/metrics')
def metrics():
    try:
        ram_metrics = get_ram_usage()
        thread_count = get_thread_count()
        return jsonify({
            'ram': ram_metrics,
            'threads': thread_count
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == "__main__":
    app.run(debug=True)