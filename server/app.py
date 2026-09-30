import os
import sqlite3
from datetime import datetime, timezone
from flask import Flask, jsonify, request, render_template

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "locations.db")

API_TOKEN = os.environ.get("LOCATION_API_TOKEN", "change-this-token")

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates")
)


def get_db():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_database():
    connection = get_db()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            accuracy REAL,
            recorded_at TEXT NOT NULL
        )
    """)

    connection.commit()
    connection.close()


def check_token():
    return request.headers.get("X-Location-Token") == API_TOKEN


@app.get("/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "Live Location V1"
    })


@app.post("/api/location")
def receive_location():

    if not check_token():
        return jsonify({
            "error": "unauthorized"
        }), 401

    data = request.get_json(silent=True) or {}

    device_id = str(data.get("device_id", "")).strip()
    latitude = data.get("latitude")
    longitude = data.get("longitude")
    accuracy = data.get("accuracy")

    if not device_id:
        return jsonify({
            "error": "device_id is required"
        }), 400

    if latitude is None or longitude is None:
        return jsonify({
            "error": "latitude and longitude are required"
        }), 400

    try:
        latitude = float(latitude)
        longitude = float(longitude)

        if accuracy is not None:
            accuracy = float(accuracy)

    except (TypeError, ValueError):
        return jsonify({
            "error": "invalid location values"
        }), 400

    if not -90 <= latitude <= 90:
        return jsonify({
            "error": "invalid latitude"
        }), 400

    if not -180 <= longitude <= 180:
        return jsonify({
            "error": "invalid longitude"
        }), 400

    recorded_at = datetime.now(timezone.utc).isoformat()

    connection = get_db()

    connection.execute("""
        INSERT INTO locations
        (device_id, latitude, longitude, accuracy, recorded_at)
        VALUES (?, ?, ?, ?, ?)
    """, (
        device_id,
        latitude,
        longitude,
        accuracy,
        recorded_at
    ))

    connection.commit()
    connection.close()

    return jsonify({
        "status": "saved",
        "device_id": device_id,
        "latitude": latitude,
        "longitude": longitude,
        "accuracy": accuracy,
        "recorded_at": recorded_at
    })


@app.get("/api/latest")
def latest_location():

    connection = get_db()

    row = connection.execute("""
        SELECT
            device_id,
            latitude,
            longitude,
            accuracy,
            recorded_at
        FROM locations
        ORDER BY id DESC
        LIMIT 1
    """).fetchone()

    connection.close()

    if row is None:
        return jsonify({
            "location": None
        })

    return jsonify(dict(row))


@app.get("/")
def dashboard():
    return render_template("index.html")


init_database()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
