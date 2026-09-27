"""
ABVP Yuvati Sammelan - Backend Server
--------------------------------------
Serves the existing static website and stores registrations
in PostgreSQL when DATABASE_URL is available.

For local development, it falls back to SQLite.

Run with:
    pip install -r requirements.txt
    python app.py

Then open:
    http://localhost:5000
"""

import os
import sqlite3
from pathlib import Path
from datetime import datetime

from flask import Flask, request, jsonify, send_from_directory


BASE_DIR = Path(__file__).resolve().parent

DATABASE_URL = os.environ.get("DATABASE_URL")

SQLITE_DB_PATH = BASE_DIR / "data" / "registrations.db"


app = Flask(
    __name__,
    static_folder=str(BASE_DIR),
    static_url_path=""
)


# ---------------------------------------------------------------
# DATABASE CONNECTION
# ---------------------------------------------------------------

def get_db_connection():

    if DATABASE_URL:

        import psycopg

        return psycopg.connect(
            DATABASE_URL
        )

    SQLITE_DB_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    conn = sqlite3.connect(
        SQLITE_DB_PATH
    )

    return conn


# ---------------------------------------------------------------
# DATABASE INITIALIZATION
# ---------------------------------------------------------------

def init_db():

    conn = get_db_connection()

    try:

        if DATABASE_URL:

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS registrations (
                    id SERIAL PRIMARY KEY,
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

        else:

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

    finally:

        conn.close()


# ---------------------------------------------------------------
# INITIALIZE DATABASE WHEN SERVER STARTS
# ---------------------------------------------------------------

init_db()


# ---------------------------------------------------------------
# SERVE THE EXISTING FRONTEND
# ---------------------------------------------------------------

@app.route("/")
def serve_index():

    return send_from_directory(
        app.static_folder,
        "index.html"
    )


@app.route("/<path:path>")
def serve_static(path):

    return send_from_directory(
        app.static_folder,
        path
    )


# ---------------------------------------------------------------
# REGISTRATION API
# ---------------------------------------------------------------

REQUIRED_FIELDS = [
    "full_name",
    "whatsapp",
    "profession",
    "college",
    "education",
    "year",
    "address"
]


@app.route("/api/register", methods=["POST"])
def register():

    data = request.get_json(
        silent=True
    ) or {}


    missing = [
        field
        for field in REQUIRED_FIELDS
        if not str(
            data.get(field, "")
        ).strip()
    ]


    if missing:

        return jsonify({
            "success": False,
            "message":
                f"Missing required fields: {', '.join(missing)}"
        }), 400


    try:

        conn = get_db_connection()


        if DATABASE_URL:

            conn.execute(
                """
                INSERT INTO registrations
                (
                    full_name,
                    whatsapp,
                    profession,
                    college,
                    education,
                    year,
                    address,
                    submitted_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    data["full_name"].strip(),
                    data["whatsapp"].strip(),
                    data["profession"].strip(),
                    data["college"].strip(),
                    data["education"].strip(),
                    data["year"].strip(),
                    data["address"].strip(),
                    datetime.now().isoformat(
                        timespec="seconds"
                    ),
                ),
            )


        else:

            conn.execute(
                """
                INSERT INTO registrations
                (
                    full_name,
                    whatsapp,
                    profession,
                    college,
                    education,
                    year,
                    address,
                    submitted_at
                )
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
                    datetime.now().isoformat(
                        timespec="seconds"
                    ),
                ),
            )


        conn.commit()
        conn.close()


    except Exception as exc:

        print(
            "Registration database error:",
            exc
        )

        return jsonify({
            "success": False,
            "message":
                "Unable to save registration."
        }), 500


    return jsonify({
        "success": True,
        "message":
            "Registration saved."
    }), 201


# ---------------------------------------------------------------
# LOCAL DEVELOPMENT
# ---------------------------------------------------------------

if __name__ == "__main__":

    init_db()

    app.run(
        debug=True,
        port=5000
    )