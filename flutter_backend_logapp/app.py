from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import subprocess
import threading
import os
import requests  # make sure requests is installed!
import time

app = Flask(__name__, static_folder='build/web', static_url_path='')
CORS(app)

# Sensorlogger server info
SENSORLOGGER_HOST = 'localhost'
SENSORLOGGER_PORT = 8000
SENSORLOGGER_URL = f'http://{SENSORLOGGER_HOST}:{SENSORLOGGER_PORT}'

# Process to run sensorlogger_postgresql.py if you want to start it from here
sensor_process = None

@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_file(path):
    return send_from_directory(app.static_folder, path)

@app.route('/start-session', methods=['POST'])
def start_session():
    print("📥 Received start-session request")  # <-- Add this
    global sensor_process

    data = request.get_json()
    name = data.get('name')
    location = data.get('location')

    if not name or not location:
        return jsonify({'status': 'error', 'message': 'Missing name or location'}), 400

    try:
        # Launch the sensorlogger server process if not already running
        if sensor_process is None or sensor_process.poll() is not None:
            script_path = os.path.join(os.path.dirname(__file__), 'sensorlogger_postgresql.py')
            sensor_process = subprocess.Popen(['python', script_path],
                                              stdout=subprocess.PIPE,
                                              stderr=subprocess.STDOUT,
                                              text=True)
            # Optional: stream sensorlogger output to your terminal
            def stream_output(proc):
                for line in proc.stdout:
                    print("[sensorlogger]", line.strip())
            threading.Thread(target=stream_output, args=(sensor_process,), daemon=True).start()

            # Give sensorlogger a few seconds to start up before calling endpoints
            time.sleep(2)

        # Call sensorlogger to start recording
        resp = requests.post(f'{SENSORLOGGER_URL}/start-recording')
        if resp.status_code == 200:
            return jsonify({'status': 'success', 'message': 'Recording started'})
        else:
            return jsonify({'status': 'error', 'message': 'Failed to start recording'}), 500

    except Exception as e:
        print(f"Error in start_session: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/stop-session', methods=['POST'])
def stop_session():
    global sensor_process
    try:
        resp = requests.post(f'{SENSORLOGGER_URL}/stop-recording')
        if resp.status_code == 200:
            # Optionally terminate sensorlogger process if you want to fully stop it
            if sensor_process and sensor_process.poll() is None:
                sensor_process.terminate()
                sensor_process = None
            return jsonify({'status': 'success', 'message': 'Recording stopped'})
        else:
            return jsonify({'status': 'error', 'message': 'Failed to stop recording'}), 500
    except Exception as e:
        print(f"Error in stop_session: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050)

