from flask import Flask, request
import sqlite3
from datetime import datetime, timedelta

app = Flask(__name__)

DB_NAME = "attendance.db"

# ---------- DATABASE SETUP ----------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            time TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ---------- HOME ----------
@app.route("/")
def home():
    return """
    <h2>QR Attendance System (PRO VERSION)</h2>
    <p>Scan QR to mark attendance</p>
    """

# ---------- MARK ATTENDANCE ----------
@app.route("/mark")
def mark():
    name = request.args.get("name")

    if not name:
        return "No name provided"

    # Georgia time (UTC +4)
    tbilisi_time = datetime.utcnow() + timedelta(hours=4)
    time_string = tbilisi_time.strftime("%Y-%m-%d %H:%M:%S")

    # Save to database
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # ❌ prevent duplicate attendance (same day + same name)
    c.execute("""
        SELECT * FROM attendance
        WHERE name = ? AND date(time) = date('now','+4 hours')
    """, (name,))

    existing = c.fetchone()

    if existing:
        conn.close()
        return f"{name} already marked attendance today!"

    c.execute("INSERT INTO attendance (name, time) VALUES (?, ?)", (name, time_string))
    conn.commit()
    conn.close()

    return f"Attendance marked for {name} at {time_string}"

# ---------- VIEW DATA ----------
@app.route("/data")
def data():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT name, time FROM attendance ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()

    output = "<h3>Attendance Records</h3><pre>"
    for r in rows:
        output += f"{r[0]} | {r[1]}\n"
    output += "</pre>"

    return output

# ---------- RUN ----------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

