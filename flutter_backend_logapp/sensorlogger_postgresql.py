import os
import json
import threading
from datetime import datetime
from flask import Flask, request
import psycopg2

# ========== PostgreSQL Configuration ==========
DB_CONFIG = {
    "dbname": "sensorloggerdb",
    "user": "newuser",
    "password": "password",
    "host": "localhost",
    "port": "5432"
}

# Connect to PostgreSQL
conn = psycopg2.connect(**DB_CONFIG)
cursor = conn.cursor()

# ========== Flask Sensor Server ==========
FLASK_HOST = "0.0.0.0"
FLASK_PORT = 8000
server = Flask(__name__)
stop_event = threading.Event()

@server.route("/data", methods=["POST"])
def data():
    payload = json.loads(request.data).get("payload", [])

    for d in payload:
        name = d.get("name", "").lower()
        ts = datetime.fromtimestamp(d["time"] / 1e9)
        vals = d.get("values", {})

        # Default values
        x = y = z = pitch = roll = yaw = None

        if name in ("accelerometer", "gravity", "gyroscope"):
            x = vals.get("x")
            y = vals.get("y")
            z = vals.get("z")
        elif name == "orientation":
            pitch = vals.get("pitch")
            roll = vals.get("roll")
            yaw = vals.get("yaw")
        else:
            continue
        try:
            cursor.execute("""
                INSERT INTO sensor_data (timestamp, sensor, x, y, z, pitch, roll, yaw)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (ts, name, x, y, z, pitch, roll, yaw))
            conn.commit()
        except Exception as e:
            print("DB Insert Error:", e)
            conn.rollback()

    return "success"

def run_sensor_server():
    server.run(host=FLASK_HOST, port=FLASK_PORT, debug=False, use_reloader=False)

# ========== Main ==========
if __name__ == "__main__":
    print(f"[START] Sensor server at http://{FLASK_HOST}:{FLASK_PORT}/data")
    threading.Thread(target=run_sensor_server, daemon=True).start()

    try:
        while not stop_event.is_set():
            stop_event.wait(1)
    except KeyboardInterrupt:
        print("[EXIT] Ctrl+C detected, shutting down...")

    # Clean up DB connection
    cursor.close()
    conn.close()
