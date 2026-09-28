"""
ABVP Yuvati Sammelan - Backend Server
--------------------------------------
Serves the existing static website and stores registrations
in PostgreSQL when DATABASE_URL is available.

For local development, it falls back to SQLite.

Duplicate registrations are prevented using:
    1. WhatsApp number
    2. Email ID

Run with:
    pip install -r requirements.txt
    python app.py

Then open:
    http://localhost:5000
"""

import os
import sqlite3
import re

from pathlib import Path
from datetime import datetime

from flask import Flask, request, jsonify, send_from_directory


# ---------------------------------------------------------------
# BASE DIRECTORY
# ---------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent


# ---------------------------------------------------------------
# DATABASE SETTINGS
# ---------------------------------------------------------------

DATABASE_URL = os.environ.get("DATABASE_URL")

SQLITE_DB_PATH = BASE_DIR / "data" / "registrations.db"


# ---------------------------------------------------------------
# FLASK APP
# ---------------------------------------------------------------

app = Flask(
    __name__,
    static_folder=str(BASE_DIR),
    static_url_path=""
)


# ---------------------------------------------------------------
# DATABASE CONNECTION
# ---------------------------------------------------------------

def get_db_connection():

    # PostgreSQL
    if DATABASE_URL:

        import psycopg

        return psycopg.connect(
            DATABASE_URL
        )

    # SQLite
    SQLITE_DB_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    conn = sqlite3.connect(
        SQLITE_DB_PATH
    )

    return conn


# ---------------------------------------------------------------
# NORMALIZE WHATSAPP NUMBER
# ---------------------------------------------------------------

def normalize_whatsapp(number):

    """
    Removes spaces, brackets, hyphens and other characters.

    Example:
        +91 98765-43210
        +919876543210
        98765 43210

    are converted into a consistent format.
    """

    number = str(number).strip()

    # Keep digits only
    digits = re.sub(
        r"\D",
        "",
        number
    )

    # Convert Indian +91 / 91 number to last 10 digits
    if len(digits) > 10 and digits.startswith("91"):
        digits = digits[-10:]

    return digits


# ---------------------------------------------------------------
# NORMALIZE EMAIL
# ---------------------------------------------------------------

def normalize_email(email):

    """
    Removes unnecessary spaces and converts email to lowercase.
    """

    return str(email).strip().lower()


# ---------------------------------------------------------------
# DATABASE INITIALIZATION
# ---------------------------------------------------------------

def init_db():

    conn = get_db_connection()

    try:

        # -------------------------------------------------------
        # CREATE TABLE
        # -------------------------------------------------------

        if DATABASE_URL:

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS registrations (
                    id SERIAL PRIMARY KEY,
                    full_name TEXT NOT NULL,
                    whatsapp TEXT NOT NULL,
                    email TEXT,
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
                    email TEXT,
                    profession TEXT,
                    college TEXT,
                    education TEXT,
                    year TEXT,
                    address TEXT,
                    submitted_at TEXT NOT NULL
                )
                """
            )

        # -------------------------------------------------------
        # DATABASE MIGRATION
        #
        # If the database already existed before email was added,
        # add the email column without deleting old registrations.
        # -------------------------------------------------------

        try:

            if DATABASE_URL:

                conn.execute(
                    """
                    ALTER TABLE registrations
                    ADD COLUMN email TEXT
                    """
                )

            else:

                conn.execute(
                    """
                    ALTER TABLE registrations
                    ADD COLUMN email TEXT
                    """
                )

        except Exception:

            # Column already exists.
            pass


        conn.commit()

    finally:

        conn.close()


# ---------------------------------------------------------------
# INITIALIZE DATABASE WHEN SERVER STARTS
# ---------------------------------------------------------------

init_db()


# ---------------------------------------------------------------
# SERVE HOME PAGE
# ---------------------------------------------------------------

@app.route("/")
def serve_index():

    return send_from_directory(
        app.static_folder,
        "index.html"
    )


# ---------------------------------------------------------------
# SERVE STATIC FILES
# ---------------------------------------------------------------

@app.route("/<path:path>")
def serve_static(path):

    return send_from_directory(
        app.static_folder,
        path
    )


# ---------------------------------------------------------------
# REQUIRED REGISTRATION FIELDS
# ---------------------------------------------------------------

REQUIRED_FIELDS = [
    "full_name",
    "whatsapp",
    "email",
    "profession",
    "college",
    "education",
    "year",
    "address"
]


# ---------------------------------------------------------------
# REGISTRATION API
# ---------------------------------------------------------------

@app.route(
    "/api/register",
    methods=["POST"]
)
def register():

    # -----------------------------------------------------------
    # GET JSON DATA
    # -----------------------------------------------------------

    data = request.get_json(
        silent=True
    ) or {}


    # -----------------------------------------------------------
    # CHECK REQUIRED FIELDS
    # -----------------------------------------------------------

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


    # -----------------------------------------------------------
    # NORMALIZE INPUT
    # -----------------------------------------------------------

    full_name = str(
        data["full_name"]
    ).strip()

    whatsapp = normalize_whatsapp(
        data["whatsapp"]
    )

    email = normalize_email(
        data["email"]
    )

    profession = str(
        data["profession"]
    ).strip()

    college = str(
        data["college"]
    ).strip()

    education = str(
        data["education"]
    ).strip()

    year = str(
        data["year"]
    ).strip()

    address = str(
        data["address"]
    ).strip()


    # -----------------------------------------------------------
    # BASIC WHATSAPP VALIDATION
    # -----------------------------------------------------------

    if len(whatsapp) != 10:

        return jsonify({
            "success": False,
            "message":
                "Please enter a valid 10-digit WhatsApp number."
        }), 400


    # -----------------------------------------------------------
    # BASIC EMAIL VALIDATION
    # -----------------------------------------------------------

    email_pattern = (
        r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    )

    if not re.match(
        email_pattern,
        email
    ):

        return jsonify({
            "success": False,
            "message":
                "Please enter a valid Email ID."
        }), 400


    # -----------------------------------------------------------
    # DATABASE OPERATION
    # -----------------------------------------------------------

    conn = None

    try:

        conn = get_db_connection()


        # -------------------------------------------------------
        # CHECK DUPLICATE WHATSAPP OR EMAIL
        # -------------------------------------------------------

        if DATABASE_URL:

            existing = conn.execute(
                """
                SELECT id, whatsapp, email
                FROM registrations
                WHERE whatsapp = %s
                   OR LOWER(email) = %s
                LIMIT 1
                """,
                (
                    whatsapp,
                    email
                )
            ).fetchone()

        else:

            existing = conn.execute(
                """
                SELECT id, whatsapp, email
                FROM registrations
                WHERE whatsapp = ?
                   OR LOWER(email) = ?
                LIMIT 1
                """,
                (
                    whatsapp,
                    email
                )
            ).fetchone()


        # -------------------------------------------------------
        # DUPLICATE FOUND
        # -------------------------------------------------------

        if existing:

            existing_whatsapp = str(
                existing[1]
            ).strip()

            existing_email = (
                str(existing[2]).strip().lower()
                if existing[2]
                else ""
            )


            # Both match
            if (
                existing_whatsapp == whatsapp
                and existing_email == email
            ):

                message = (
                    "This WhatsApp number and Email ID "
                    "are already registered."
                )

            # WhatsApp match
            elif existing_whatsapp == whatsapp:

                message = (
                    "This WhatsApp number "
                    "is already registered."
                )

            # Email match
            else:

                message = (
                    "This Email ID "
                    "is already registered."
                )


            conn.close()
            conn = None

            return jsonify({
                "success": False,
                "message": message
            }), 409


        # -------------------------------------------------------
        # INSERT NEW REGISTRATION - POSTGRESQL
        # -------------------------------------------------------

        if DATABASE_URL:

            conn.execute(
                """
                INSERT INTO registrations
                (
                    full_name,
                    whatsapp,
                    email,
                    profession,
                    college,
                    education,
                    year,
                    address,
                    submitted_at
                )
                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
                """,
                (
                    full_name,
                    whatsapp,
                    email,
                    profession,
                    college,
                    education,
                    year,
                    address,
                    datetime.now().isoformat(
                        timespec="seconds"
                    ),
                ),
            )


        # -------------------------------------------------------
        # INSERT NEW REGISTRATION - SQLITE
        # -------------------------------------------------------

        else:

            conn.execute(
                """
                INSERT INTO registrations
                (
                    full_name,
                    whatsapp,
                    email,
                    profession,
                    college,
                    education,
                    year,
                    address,
                    submitted_at
                )
                VALUES
                (
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?
                )
                """,
                (
                    full_name,
                    whatsapp,
                    email,
                    profession,
                    college,
                    education,
                    year,
                    address,
                    datetime.now().isoformat(
                        timespec="seconds"
                    ),
                ),
            )


        # -------------------------------------------------------
        # SAVE
        # -------------------------------------------------------

        conn.commit()


        return jsonify({
            "success": True,
            "message":
                "Registration saved successfully."
        }), 201


    # -----------------------------------------------------------
    # DATABASE ERROR
    # -----------------------------------------------------------

    except Exception as exc:

        print(
            "Registration database error:",
            exc
        )

        if conn:

            try:
                conn.rollback()
            except Exception:
                pass

        return jsonify({
            "success": False,
            "message":
                "Unable to save registration."
        }), 500


    finally:

        if conn:

            try:
                conn.close()
            except Exception:
                pass


# ---------------------------------------------------------------
# LOCAL DEVELOPMENT
# ---------------------------------------------------------------

if __name__ == "__main__":

    init_db()

    app.run(
        debug=True,
        port=5000
    )