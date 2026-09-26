"""
ABVP Yuvati Sammelan - Backend Server
--------------------------------------
Serves the existing static website (index.html, registration.html,
css/, images/, js/) exactly as-is, and adds one API endpoint:

    POST /api/register   -> saves a registration into registrations.db (SQLite)

Run with:
    pip install -r requirements.txt
    python app.py

Then open:
    http://localhost:5000
"""

import sqlite3
from pathlib import Path
from datetime import datetime

from flask import Flask, request, jsonify, send_from_directory

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "registrations.db"

app = Flask(__name__, static_folder=str(BASE_DIR), static_url_path="")


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS registrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            whatsapp TEXT NOT NULL,
            profession TEXT,
            college TEXT,
            education TEXT,
            year TEXT,
            address TEXT,
            submitted_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------
# Serve the existing frontend, unchanged
# ---------------------------------------------------------------
@app.route("/")
def serve_index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/<path:path>")
def serve_static(path):
    return send_from_directory(app.static_folder, path)


# ---------------------------------------------------------------
# Registration API
# ---------------------------------------------------------------
REQUIRED_FIELDS = [
    "full_name", "whatsapp", "profession",
    "college", "education", "year", "address"
]


@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}

    missing = [f for f in REQUIRED_FIELDS if not str(data.get(f, "")).strip()]
    if missing:
        return jsonify({
            "success": False,
            "message": f"Missing required fields: {', '.join(missing)}"
        }), 400

    try:
        conn = get_db_connection()
        conn.execute(
            """
            INSERT INTO registrations
                (full_name, whatsapp, profession, college, education, year, address, submitted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["full_name"].strip(),
                data["whatsapp"].strip(),
                data["profession"].strip(),
                data["college"].strip(),
                data["education"].strip(),
                data["year"].strip(),
                data["address"].strip(),
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        conn.commit()
        conn.close()
    except Exception as exc:  # noqa: BLE001
        return jsonify({"success": False, "message": f"Server error: {exc}"}), 500

    return jsonify({"success": True, "message": "Registration saved."}), 201


# Optional: quick way to see saved registrations in the browser as JSON
@app.route("/api/registrations", methods=["GET"])
def list_registrations():
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT * FROM registrations ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)