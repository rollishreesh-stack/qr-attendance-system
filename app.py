import os
import sys
import sqlite3
import secrets
import qrcode
import zipfile
import io
from datetime import datetime, timedelta

from flask import Flask, request, redirect, send_file, render_template_string, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd

# ================= SAFE GRAPHING ENGINE CONTEXT =================
CHARTS_ENABLED = True
try:
    import matplotlib
    matplotlib.use('Agg')  # Configures headless background rendering for Linux servers
    import matplotlib.pyplot as plt
except Exception as e:
    print("SYSTEM NOTICE: Disabling analytics chart layer safely.")
    CHARTS_ENABLED = False

# ================= APP INITIALIZATION =================
app = Flask(__name__)
app.secret_key = "supersecretkey"

DB_NAME = "attendance.db"

# ================= PREMIUM DATABASE CONFIGURATION =================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS admin_users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        token TEXT UNIQUE NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        time TEXT NOT NULL
    )
    """)

    try:
        c.execute("CREATE INDEX IF NOT EXISTS idx_students_token ON students(token)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_attendance_name_time ON attendance(name, time)")
    except Exception as e:
        print("Performance indexing notice:", e)

    c.execute("SELECT COUNT(*) FROM admin_users")
    if c.fetchone()[0] == 0:
        hashed_pw = generate_password_hash("admin123")
        c.execute("INSERT INTO admin_users (username, password) VALUES (?, ?)", ("admin", hashed_pw))

    conn.commit()
    conn.close()

init_db()

# ================= LOGIN MANAGER =================
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, username FROM admin_users WHERE id=?", (user_id,))
    data = c.fetchone()
    conn.close()
    if data:
        return User(data[0], data[1])
    return None

# ================= EXECUTIVE MASTER LAYOUT =================
LAYOUT_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AIMCS | Executive Attendance Command</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <script src="https://cdn.jsdelivr.net/npm/@emailjs/browser@4/dist/email.min.js"></script>
    <script>
        (function(){
            emailjs.init("-oGl3hn1HEMpvxh2T");
        })();
    </script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght=300;400;500;600;700&display=swap');
        body { font-family: 'Plus Jakarta Sans', sans-serif; background-color: #090d16; }
        ::-webkit-scrollbar { width: 5px; height: 5px; }
        ::-webkit-scrollbar-track { background: #090d16; }
        ::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 10px; }
    </style>
</head>
<body class="text-slate-300 min-h-screen flex">

    {% if current_user.is_authenticated %}
    <aside class="w-80 bg-[#0f1524] border-r border-slate-800/60 flex flex-col fixed h-full z-20">
        <div class="p-7 border-b border-slate-800/60 flex items-center gap-3.5">
            <div class="bg-gradient-to-tr from-blue-600 to-indigo-600 p-2.5 rounded-xl text-white shadow-lg shadow-blue-500/20">
                <i class="fa-solid fa-shield-halved text-lg"></i>
            </div>
            <div>
                <h1 class="text-lg font-bold text-white tracking-wide">AIMCS Engine</h1>
                <p class="text-[10px] text-slate-500 font-semibold tracking-wider uppercase">Enterprise Control</p>
            </div>
        </div>
        
        <nav class="flex-1 p-5 space-y-2 mt-4">
            <a href="/" class="flex items-center gap-3.5 px-4 py-3 rounded-xl text-xs font-semibold tracking-wide uppercase transition-all text-slate-400 hover:bg-slate-800/40 hover:text-white">
                <i class="fa-solid fa-cube text-sm w-5 text-slate-500"></i> Main Hub
            </a>
            <a href="/dashboard" class="flex items-center gap-3.5 px-4 py-3 rounded-xl text-xs font-semibold tracking-wide uppercase transition-all text-slate-400 hover:bg-slate-800/40 hover:text-white">
                <i class="fa-solid fa-gauge-high text-sm w-5 text-slate-500"></i> Performance Control
            </a>
            <a href="/bulk" class="flex items-center gap-3.5 px-4 py-3 rounded-xl text-xs font-semibold tracking-wide uppercase transition-all text-slate-400 hover:bg-slate-800/40 hover:text-white">
                <i class="fa-solid fa-bolt text-sm w-5 text-slate-500"></i> Batch Engine
            </a>
            <a href="/analysis" class="flex items-center gap-3.5 px-4 py-3 rounded-xl text-xs font-semibold tracking-wide uppercase transition-all text-slate-400 hover:bg-slate-800/40 hover:text-white">
                <i class="fa-solid fa-chart-line text-sm w-5 text-slate-500"></i> Analytics Layer
            </a>
            <a href="/profile" class="flex items-center gap-3.5 px-4 py-3 rounded-xl text-xs font-semibold tracking-wide uppercase transition-all text-slate-400 hover:bg-slate-800/40 hover:text-white">
                <i class="fa-solid fa-sliders text-sm w-5 text-slate-500"></i> Identity Vault
            </a>
            <a href="/logout" class="flex items-center gap-3.5 px-4 py-3 rounded-xl text-xs font-semibold tracking-wide uppercase transition-all text-rose-400 hover:bg-rose-500/5 hover:text-rose-300">
                <i class="fa-solid fa-power-off text-sm w-5"></i> Kill Session
            </a>
        </nav>

        <div class="p-5 border-t border-slate-800/60">
            <div class="bg-slate-900/60 p-4 rounded-xl border border-slate-800/50 flex items-center gap-3">
                <div class="w-8 h-8 rounded-lg bg-gradient-to-tr from-blue-500 to-indigo-500 text-white flex items-center justify-center font-bold text-xs shadow-md">
                    {{ current_user.username[0].upper() if current_user.username else 'A' }}
                </div>
                <div class="truncate">
                    <p class="text-xs font-bold text-white truncate">{{ current_user.username }}</p>
                    <p class="text-[9px] font-mono text-emerald-400 uppercase tracking-wider">SECURE CONNECTED</p>
                </div>
            </div>
        </div>
    </aside>
    {% endif %}

    <main class="flex-1 {% if current_user.is_authenticated %}pl-80{% endif %} min-h-screen flex flex-col">
        <header class="h-20 bg-[#0f1524]/40 backdrop-blur-md border-b border-slate-800/60 flex items-center justify-between px-8 sticky top-0 z-10">
            <div class="flex items-center gap-2.5">
                <span class="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                <p class="text-[10px] font-bold tracking-widest text-slate-400 uppercase">SYS_NODE_OK // MATRIX_ACTIVE</p>
            </div>
            <div class="text-xs font-semibold tracking-wide text-slate-300 bg-slate-900/80 px-4 py-2 rounded-xl border border-slate-800/40">
                <i class="fa-regular fa-clock mr-2 text-blue-400"></i> <span id="liveClock" class="font-mono"></span>
            </div>
        </header>

        <div class="p-8 flex-1 flex flex-col justify-start">
            {{ content | safe }}
        </div>
    </main>

    <script>
        function updateClock() {
            const now = new Date();
            document.getElementById('liveClock').innerText = now.toLocaleString();
        }
        setInterval(updateClock, 1000);
        updateClock();
    </script>
</body>
</html>
"""

# ================= LOGIN ROUTE =================
@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("home"))
        
    error_msg = ""
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT id, username, password FROM admin_users WHERE username=?", (username,))
        admin_data = c.fetchone()
        conn.close()
        
        if admin_data and check_password_hash(admin_data[2], password):
            userobj = User(admin_data[0], admin_data[1])
            login_user(userobj)
            return redirect(url_for("home"))
        else:
            error_msg = "Verification mismatch. Identity rejection logged."

    content = f"""
    <div class="max-w-md w-full mx-auto my-auto bg-[#0f1524] border border-slate-800/80 rounded-2xl p-8 space-y-6 shadow-2xl">
        <div class="text-center space-y-2">
            <div class="inline-flex p-3.5 bg-gradient-to-tr from-blue-600/10 to-indigo-600/10 border border-blue-500/20 text-blue-400 rounded-xl mb-1 shadow-inner">
                <i class="fa-solid fa-vault text-xl"></i>
            </div>
            <h2 class="text-xl font-bold text-white tracking-tight">AIMCS Secure Token Ingestion</h2>
            <p class="text-[11px] text-slate-400 uppercase tracking-wider font-semibold">System Administrator Authentication</p>
        </div>
        
        {f'<div class="p-3 bg-rose-500/5 border border-rose-500/20 text-rose-400 text-xs rounded-xl font-semibold text-center tracking-wide">{error_msg}</div>' if error_msg else ''}

        <form method="POST" class="space-y-4">
            <div class="space-y-1.5">
                <label class="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Operator Signature ID</label>
                <input type="text" name="username" class="w-full bg-[#090d16] border border-slate-800 rounded-xl px-4 py-3 text-xs text-white focus:outline-none focus:border-blue-500/80 transition-colors font-medium tracking-wide" placeholder="e.g. admin" required>
            </div>
            <div class="space-y-1.5">
                <label class="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Cryptographic Passphrase</label>
                <input type="password" name="password" class="w-full bg-[#090d16] border border-slate-800 rounded-xl px-4 py-3 text-xs text-white focus:outline-none focus:border-blue-500/80 transition-colors font-medium tracking-wide" placeholder="••••••••" required>
            </div>
            <button type="submit" class="w-full inline-flex items-center justify-center px-4 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-semibold rounded-xl text-xs tracking-wider uppercase transition-all shadow-lg shadow-blue-500/10">
                Establish Connection Node
            </button>
        </form>
    </div>
    """
    return render_template_string(LAYOUT_TEMPLATE, content=content)

# ================= LOGOUT ROUTE =================
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

# ================= PROFILE/CHANGE PASSWORD =================
@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    status_msg = ""
    if request.method == "POST":
        old_pass = request.form["old_password"]
        new_pass = request.form["new_password"]
        
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT password FROM admin_users WHERE id=?", (current_user.id,))
        current_pw_hash = c.fetchone()[0]
        
        if check_password_hash(current_pw_hash, old_pass):
            new_hash = generate_password_hash(new_pass)
            c.execute("UPDATE admin_users SET password=? WHERE id=?", (new_hash, current_user.id))
            conn.commit()
            status_msg = """<div class="p-3 bg-emerald-500/5 border border-emerald-500/20 text-emerald-400 text-xs rounded-xl font-semibold text-center tracking-wide">Key infrastructure modification executed successfully.</div>"""
        else:
            status_msg = """<div class="p-3 bg-rose-500/5 border border-rose-500/20 text-rose-400 text-xs rounded-xl font-semibold text-center tracking-wide">Signature mismatch. Vault access rejected.</div>"""
        conn.close()

    content = f"""
    <div class="max-w-xl mx-auto bg-[#0f1524] border border-slate-800/80 rounded-2xl p-8 space-y-6 shadow-2xl">
        <div>
            <h2 class="text-lg font-bold text-white tracking-tight">Identity Vault Configuration</h2>
            <p class="text-xs text-slate-400 mt-1">Alter underlying connection string parameters dynamically.</p>
        </div>

        {status_msg}

        <form method="POST" class="space-y-4">
            <div class="space-y-1.5">
                <label class="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Active Verification Key</label>
                <input type="password" name="old_password" class="w-full bg-[#090d16] border border-slate-800 rounded-xl px-4 py-3 text-xs text-white focus:outline-none focus:border-blue-500/80 transition-colors font-medium tracking-wide" required>
            </div>
            <div class="space-y-1.5">
                <label class="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Target Generation Key</label>
                <input type="password" name="new_password" class="w-full bg-[#090d16] border border-slate-800 rounded-xl px-4 py-3 text-xs text-white focus:outline-none focus:border-blue-500/80 transition-colors font-medium tracking-wide" required>
            </div>
            <button type="submit" class="w-full inline-flex items-center justify-center px-4 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-semibold rounded-xl text-xs tracking-wider uppercase transition-all shadow-lg shadow-blue-500/10">
                Commit Changes
            </button>
        </form>
    </div>
    """
    return render_template_string(LAYOUT_TEMPLATE, content=content)

# ================= HOME =================
@app.route("/")
@login_required
def home():
    content = """
    <div class="max-w-3xl mx-auto mt-16 text-center space-y-6">
        <div class="inline-flex p-5 bg-gradient-to-tr from-blue-600/10 to-indigo-600/10 text-blue-400 rounded-3xl border border-blue-500/20 shadow-2xl mb-2">
            <i class="fa-solid fa-chess-knight text-4xl"></i>
        </div>
        <h2 class="text-3xl font-extrabold text-white tracking-tight sm:text-4xl">
            AIMCS Core Matrix Hub
        </h2>
        <p class="text-sm text-slate-400 max-w-xl mx-auto leading-relaxed font-medium">
            High-integrity digital ledger, structural identity array validations, automatic pipeline reporting nodes, and live analytical telemetry visualization.
        </p>
        <div class="pt-4">
            <a href="/dashboard" class="inline-flex items-center justify-center px-6 py-3.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-bold rounded-xl text-xs uppercase tracking-wider transition-all shadow-lg shadow-blue-500/20 hover:scale-[1.01]">
                Launch Command Panel <i class="fa-solid fa-arrow-right-long ml-2 text-xs"></i>
            </a>
        </div>
    </div>
    """
    return render_template_string(LAYOUT_TEMPLATE, content=content)

# ================= DASHBOARD =================
@app.route("/dashboard")
@login_required
def dashboard():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM students")
    students = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM attendance")
    attendance = c.fetchone()[0]
    conn.close()

    content = f"""
    <div class="space-y-8">
        <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
            <div>
                <h2 class="text-xl font-bold text-white tracking-tight">Analytical Telemetry Control</h2>
                <p class="text-xs text-slate-400">AIMCS high-performance storage array processing context data metrics.</p>
            </div>
            <div class="flex items-center gap-2 bg-[#0f1524] border border-slate-800/80 p-1.5 rounded-xl shadow-md">
                <a href="/bulk" class="px-4 py-2.5 text-[11px] font-bold tracking-wider uppercase bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white rounded-lg transition-all flex items-center gap-2">
                    <i class="fa-solid fa-plus text-[9px]"></i> New Matrix Session
                </a>
            </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <div class="bg-[#0f1524] border border-slate-800/60 p-6 rounded-2xl flex items-center justify-between shadow-xl">
                <div class="space-y-1">
                    <p class="text-xs font-bold text-slate-400 uppercase tracking-wider">Indexed Identities</p>
                    <h3 class="text-2xl font-bold text-white tracking-tight">{students}</h3>
                </div>
                <div class="h-11 w-11 bg-blue-500/5 border border-blue-500/20 text-blue-400 rounded-xl flex items-center justify-center text-lg shadow-inner">
                    <i class="fa-solid fa-fingerprint"></i>
                </div>
            </div>

            <div class="bg-[#0f1524] border border-slate-800/60 p-6 rounded-2xl flex items-center justify-between shadow-xl">
                <div class="space-y-1">
                    <p class="text-xs font-bold text-slate-400 uppercase tracking-wider">Processed Ingestions</p>
                    <h3 class="text-2xl font-bold text-emerald-400 tracking-tight">{attendance}</h3>
                </div>
                <div class="h-11 w-11 bg-emerald-500/5 border border-emerald-500/20 text-emerald-400 rounded-xl flex items-center justify-center text-lg shadow-inner">
                    <i class="fa-solid fa-network-wired"></i>
                </div>
            </div>

            <div class="bg-[#0f1524] border border-slate-800/60 p-6 rounded-2xl flex items-center justify-between md:col-span-2 lg:col-span-1 shadow-xl">
                <div class="space-y-1">
                    <p class="text-xs font-bold text-slate-400 uppercase tracking-wider">Relational Array Engine</p>
                    <h3 class="text-sm font-bold text-white tracking-tight">Structured SQLite Layer</h3>
                </div>
                <div class="h-11 w-11 bg-purple-500/5 border border-purple-500/20 text-purple-400 rounded-xl flex items-center justify-center text-lg shadow-inner">
                    <i class="fa-solid fa-microchip"></i>
                </div>
            </div>
        </div>

        <div class="bg-[#0f1524] border border-slate-800/60 rounded-2xl p-6 shadow-xl">
            <div class="flex justify-between items-center mb-6 border-b border-slate-800/60 pb-4">
                <h3 class="text-xs font-bold text-white uppercase tracking-wider">Data Extraction Management Pipe</h3>
                <span class="text-[9px] bg-slate-900 border border-slate-800 px-2.5 py-1 rounded-md text-slate-400 font-mono font-bold tracking-widest">HIGH SPEED GATEWAY</span>
            </div>
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <a href="/bulk" class="flex items-center gap-4 p-4 bg-slate-900/40 hover:bg-slate-800/20 rounded-xl border border-slate-800/40 transition-all group">
                    <div class="h-9 w-9 bg-blue-500/5 border border-blue-500/20 text-blue-400 rounded-lg flex items-center justify-center text-sm group-hover:scale-105 transition-transform shadow-inner">
                        <i class="fa-solid fa-qrcode"></i>
                    </div>
                    <div>
                        <span class="text-xs font-bold text-white block tracking-wide uppercase">Token Batching Engine</span>
                        <span class="text-[10px] text-slate-500 font-medium block mt-0.5">Initialize dynamic scan arrays</span>
                    </div>
                </a>
                <a href="/download" class="flex items-center gap-4 p-4 bg-slate-900/40 hover:bg-slate-800/20 rounded-xl border border-slate-800/40 transition-all group">
                    <div class="h-9 w-9 bg-emerald-500/5 border border-emerald-500/20 text-emerald-400 rounded-lg flex items-center justify-center text-sm group-hover:scale-105 transition-transform shadow-inner">
                        <i class="fa-solid fa-file-csv"></i>
                    </div>
                    <div>
                        <span class="text-xs font-bold text-white block tracking-wide uppercase">Export Ledger Matrices</span>
                        <span class="text-[10px] text-slate-500 font-medium block mt-0.5">Extract core tabular Excel files</span>
                    </div>
                </a>
                <a href="/download_qrs" class="flex items-center gap-4 p-4 bg-slate-900/40 hover:bg-slate-800/20 rounded-xl border border-slate-800/40 transition-all group">
                    <div class="h-9 w-9 bg-amber-500/5 border border-amber-500/20 text-amber-400 rounded-lg flex items-center justify-center text-sm group-hover:scale-105 transition-transform shadow-inner">
                        <i class="fa-solid fa-box-archive"></i>
                    </div>
                    <div>
                        <span class="text-xs font-bold text-white block tracking-wide uppercase">Download QR Archive</span>
                        <span class="text-[10px] text-slate-500 font-medium block mt-0.5">Compress token batches into ZIP</span>
                    </div>
                </a>
            </div>
        </div>
    </div>
    """
    return render_template_string(LAYOUT_TEMPLATE, content=content)

# ================= BULK QR + EMAIL =================
@app.route("/bulk", methods=["GET","POST"])
@login_required
def bulk():
    if request.method == "POST":
        start_time = request.form["start_time"]
        end_time = request.form["end_time"]
        data = request.form["data"]
        lines = data.strip().split("\n")

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        os.makedirs("static/qrs", exist_ok=True)

        success = 0
        js_students = []

        for line in lines:
            try:
                line = line.strip()
                if not line or "," not in line:
                    continue

                name, email = line.split(",", 1)
                name = name.strip()
                email = email.strip()

                token = secrets.token_hex(8)

                c.execute("""
                INSERT INTO students (name,email,token,start_time,end_time)
                VALUES (?,?,?,?,?)
                """, (name, email, token, start_time, end_time))

                qr_link = request.host_url + "mark/" + token
                qr_image_url = "https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=" + qr_link

                img = qrcode.make(qr_link)
                file_path = f"static/qrs/{name.replace(' ','_')}.png"
                img.save(file_path)

                js_students.append(f"{name},{email},{qr_link},{qr_image_url}")
                success += 1
            except Exception as e:
                print("ERROR:", e)

        conn.commit()
        conn.close()
        js_data = "\n".join(js_students)

        content = f"""
        <div class="max-w-2xl mx-auto bg-[#0f1524] border border-slate-800/80 rounded-2xl p-8 text-center space-y-6 shadow-2xl">
            <div class="inline-flex p-4 bg-emerald-500/5 text-emerald-400 rounded-full border border-emerald-500/20 shadow-xl">
                <i class="fa-solid fa-square-poll-horizontal text-3xl"></i>
            </div>
            <h2 class="text-xl font-bold text-white tracking-tight">AIMCS Pipeline Verification Implemented</h2>
            <p class="text-slate-400 text-xs max-w-sm mx-auto font-medium">
                Successfully registered <span class="text-white font-bold">{success}</span> execution targets inside the ledger core database. Automated communication dispatches processing.
            </p>

            <script>
            const students = `{js_data}`.trim().split('\\n');
            students.forEach(s => {{
                let p = s.split(",");
                if (p.length < 4) return;
                emailjs.send("service_iuneir8", "template_uyhe7xo", {{
                    name: p[0],
                    email: p[1],
                    qr_link: p[2],
                    qr_image: p[3]
                }});
            }});
            </script>

            <div class="pt-4 border-t border-slate-800/60">
                <a href='/dashboard' class="inline-flex w-full items-center justify-center px-4 py-3 bg-slate-900 hover:bg-slate-800 border border-slate-800 text-xs font-bold tracking-wider uppercase text-white rounded-xl transition-colors">
                    Return to Operational Panel
                </a>
            </div>
        </div>
        """
        return render_template_string(LAYOUT_TEMPLATE, content=content)

    content = """
    <div class="max-w-3xl mx-auto bg-[#0f1524] border border-slate-800/80 rounded-2xl p-8 space-y-6 shadow-2xl">
        <div>
            <h2 class="text-lg font-bold text-white tracking-tight">Token Allocation & Session Configurator</h2>
            <p class="text-xs text-slate-400 mt-1">Configure structural dataset elements and access windows bounds parameters.</p>
        </div>

        <form method='POST' class="space-y-5">
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div class="space-y-1.5">
                    <label class='text-[10px] font-bold text-slate-400 uppercase tracking-widest'>Validation Bounds Initialization</label>
                    <input type='datetime-local' name='start_time' class='w-full bg-[#090d16] border border-slate-800 rounded-xl px-4 py-3 text-xs text-white focus:outline-none focus:border-blue-500/80 transition-colors font-medium' required>
                </div>
                <div class="space-y-1.5">
                    <label class='text-[10px] font-bold text-slate-400 uppercase tracking-widest'>Validation Bounds Termination</label>
                    <input type='datetime-local' name='end_time' class='w-full bg-[#090d16] border border-slate-800 rounded-xl px-4 py-3 text-xs text-white focus:outline-none focus:border-blue-500/80 transition-colors font-medium' required>
                </div>
            </div>

            <div class="space-y-1.5">
                <label class='text-[10px] font-bold text-slate-400 uppercase tracking-widest'>Identity Array Source Data (Format: Full Name, Active Email)</label>
                <textarea name='data' class='w-full h-44 bg-[#090d16] border border-slate-800 rounded-xl p-4 text-xs text-white focus:outline-none focus:border-blue-500/80 transition-colors font-mono leading-relaxed' placeholder="Jane Doe, jane@example.com&#10;John Smith, john@example.com" required></textarea>
            </div>
            
            <button type='submit' class="w-full inline-flex items-center justify-center px-4 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-semibold rounded-xl text-xs tracking-wider uppercase transition-all shadow-lg shadow-blue-500/10">
                Execute System Generation & Signal Dispatches
            </button>
        </form>
    </div>
    """
    return render_template_string(LAYOUT_TEMPLATE, content=content)

# ================= PERFORMANCE REPORT / ANALYSIS =================
@app.route("/analysis")
@login_required
def analysis():
    conn = sqlite3.connect(DB_NAME)
    df_logs = pd.read_sql_query("SELECT * FROM attendance ORDER BY time DESC", conn)
    df_config = pd.read_sql_query("SELECT name, start_time, end_time FROM students", conn)
    conn.close()

    chart_url = ""
    if CHARTS_ENABLED and not df_logs.empty:
        try:
            df_logs['date_only'] = df_logs['time'].apply(lambda x: x.split()[0] if x else '')
            attendance_counts = df_logs.groupby('date_only').size()

            plt.figure(figsize=(7, 3.2))
            plt.gcf().patch.set_facecolor('#0f1524')
            ax = plt.gca()
            ax.set_facecolor('#0f1524')
            
            attendance_counts.plot(kind='bar', color='#2563eb', edgecolor='#3b82f6', width=0.4, ax=ax)
            ax.tick_params(colors='white', labelsize=8)
            ax.spines['bottom'].set_color('#1e293b')
            ax.spines['left'].set_color('#1e293b')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.grid(axis='y', color='#1e293b', linestyle='--', alpha=0.4)
            
            plt.title("Ingestion Analytics Timeframe", color='white', fontsize=9, pad=10, weight='bold', alpha=0.8)
            plt.tight_layout()
            
            img_buf = io.BytesIO()
            plt.savefig(img_buf, format='png', facecolor=plt.gcf().get_facecolor(), bbox_inches='tight')
            img_buf.seek(0)
            import base64
            chart_url = "data:image/png;base64," + base64.b64encode(img_buf.getvalue()).decode('utf-8')
            plt.close()
        except Exception as e:
            print("Chart Engine Runtime Handle:", e)

    table_rows = ""
    if not df_logs.empty:
        for idx, row in df_logs.iterrows():
            log_time = row['time']
            date_part = log_time.split()[0] if log_time else ""
            table_rows += f"""
            <tr class="log-row border-b border-slate-800/40 text-slate-300 text-xs hover:bg-slate-800/10 transition-colors" data-date="{date_part}">
                <td class="px-6 py-3.5 font-mono text-slate-500">#{row['id']}</td>
                <td class="px-6 py-3.5 font-bold text-white">{row['name']}</td>
                <td class="px-6 py-3.5 font-mono text-slate-400 text-[11px]">{row['time']}</td>
                <td class="px-6 py-3.5"><span class="px-2 py-0.5 bg-emerald-500/5 border border-emerald-500/20 text-emerald-400 rounded-md text-[9px] font-bold tracking-wider">VERIFIED_LEDGER</span></td>
            </tr>
            """
    else:
        table_rows = """
        <tr id="emptyRow">
            <td colspan="4" class="px-6 py-12 text-center text-xs text-slate-500 font-semibold uppercase tracking-wider">No active transactional entries detected within the target index ledger.</td>
        </tr>
        """

    today_iso = (datetime.utcnow() + timedelta(hours=4)).strftime("%Y-%m-%d")

    chart_render = f'<img src="{chart_url}" class="rounded-xl w-full" />' if chart_url else '<div class="text-slate-500 text-xs text-center py-12 font-medium">Data visualization layer active. Awaiting log profiles.</div>'
    if not CHARTS_ENABLED:
        chart_render = '<div class="text-slate-400 text-xs text-center py-12 font-semibold uppercase tracking-wider bg-slate-900/40 rounded-xl p-4 border border-slate-800/40"><i class="fa-solid fa-triangle-exclamation text-amber-500 block text-lg mb-2"></i> Cloud Core Mode Active.<br><span class="text-[10px] text-slate-500 mt-1 block">Tabular lists processing natively.</span></div>'

    content = f"""
    <div class="space-y-8">
        <div>
            <h2 class="text-xl font-bold text-white tracking-tight">Enterprise Analytics Node</h2>
            <p class="text-xs text-slate-400">AIMCS core logging metric calculations framework visualization layers.</p>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
            <div class="lg:col-span-1 bg-[#0f1524] border border-slate-800/60 rounded-2xl p-5 flex flex-col justify-center items-center shadow-xl">
                <div class="w-full border-b border-slate-800/60 pb-3 mb-4 flex items-center gap-2">
                    <i class="fa-solid fa-chart-bar text-blue-400 text-xs"></i>
                    <span class="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Statistical Graph View</span>
                </div>
                {chart_render}
            </div>
            
            <div class="lg:col-span-2 bg-[#0f1524] border border-slate-800/60 rounded-2xl p-6 space-y-4 shadow-xl">
                <div class="flex justify-between items-center border-b border-slate-800/60 pb-3">
                    <div class="flex items-center gap-2">
                        <i class="fa-solid fa-layer-group text-blue-400 text-xs"></i>
                        <h3 class="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Active System Token Configurations Table</h3>
                    </div>
                </div>
                <div class="overflow-x-auto border border-slate-800/60 rounded-xl bg-[#090d16]/30 max-h-[260px] overflow-y-auto">
                    <table class="w-full text-left border-collapse">
                        <thead class="sticky top-0 bg-[#0f1524] z-10 border-b border-slate-800/60">
                            <tr class="text-[9px] font-bold text-slate-400 uppercase tracking-widest">
                                <th class="px-6 py-3">Sequence Map</th>
                                <th class="px-6 py-3">Subject Identification Target</th>
                                <th class="px-6 py-3">Configured Session Validity Range Bound</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-slate-800/40 text-xs text-slate-300">
                            {"".join([f'<tr class="hover:bg-slate-800/5"><td class="px-6 py-3 font-mono text-slate-500">#{i+1}</td><td class="px-6 py-3 font-bold text-white">{r["name"]}</td><td class="px-6 py-3 font-mono text-slate-400 text-[11px]">{r["start_time"]} &rarr; {r["end_time"]}</td></tr>' for i, r in df_config.iterrows()]) if not df_config.empty else '<tr><td colspan="3" class="px-6 py-6 text-center text-slate-500 uppercase text-[10px] tracking-wider">Empty structural mapping records.</td></tr>'}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <div class="bg-[#0f1524] border border-slate-800/60 rounded-2xl p-6 shadow-xl">
            <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6 border-b border-slate-800/60 pb-4">
                <div class="flex items-center gap-2">
                    <i class="fa-solid fa-clipboard-list text-blue-400 text-xs"></i>
                    <h3 class="text-[10px] font-bold text-white uppercase tracking-widest">Transactional Stream Ledger</h3>
                </div>
                
                <div class="flex items-center gap-2.5">
                    <label class="text-[11px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5"><i class="fa-solid fa-filter text-[9px] text-blue-400"></i> Scope Constraints:</label>
                    <select id="timeFilterMenu" onchange="runTemporalFilter()" class="bg-[#090d16] border border-slate-800 text-xs font-semibold text-slate-300 rounded-xl px-3 py-2 focus:outline-none focus:border-blue-500 cursor-pointer transition-colors">
                        <option value="all">Display Full Ledger Index</option>
                        <option value="today">Today's Validation Sequence Entries</option>
                        <option value="past">Archived Historic Logs Matrix</option>
                    </select>
                </div>
            </div>

            <div class="overflow-hidden border border-slate-800/60 rounded-xl bg-[#090d16]/30">
                <div class="max-h-96 overflow-y-auto">
                    <table class="w-full text-left border-collapse" id="logsDataTable">
                        <thead class="sticky top-0 bg-[#0f1524] border-b border-slate-800/60 text-[9px] font-bold text-slate-400 uppercase tracking-widest z-10">
                            <tr>
                                <th class="px-6 py-3">Global Index</th>
                                <th class="px-6 py-3">Validated Entity Context</th>
                                <th class="px-6 py-3">Ingestion Datetime Mapping</th>
                                <th class="px-6 py-3">Network Pipeline State</th>
                            </tr>
                        </thead>
                        <tbody>
                            {table_rows}
                        </tbody>
                    </table>
                    <div id="noLogsFallback" class="hidden px-6 py-12 text-center text-xs text-slate-500 font-bold uppercase tracking-wider">No transactional metrics exist inside the matching dynamic constraint window bounds.</div>
                </div>
            </div>
        </div>
    </div>

    <script>
        function runTemporalFilter() {{
            const selectedScope = document.getElementById('timeFilterMenu').value;
            const targetDayString = "{today_iso}";
            const dataRows = document.querySelectorAll('.log-row');
            const fallbackContainer = document.getElementById('noLogsFallback');
            let matchingCounter = 0;

            dataRows.forEach(row => {{
                const instanceDate = row.getAttribute('data-date');
                if (selectedScope === 'all') {{
                    row.style.display = '';
                    matchingCounter++;
                }} else if (selectedScope === 'today') {{
                    if (instanceDate === targetDayString) {{
                        row.style.display = '';
                        matchingCounter++;
                    }} else {{
                        row.style.display = 'none';
                    }}
                }} else if (selectedScope === 'past') {{
                    if (instanceDate !== targetDayString && instanceDate !== '') {{
                        row.style.display = '';
                        matchingCounter++;
                    }} else {{
                        row.style.display = 'none';
                    }}
                }}
            }});

            const baselineFallback = document.getElementById('emptyRow');
            if(baselineFallback) {{
                fallbackContainer.style.display = 'none';
                return;
            }}

            if (matchingCounter === 0) {{
                fallbackContainer.classList.remove('hidden');
            }} else {{
                fallbackContainer.classList.add('hidden');
            }}
        }}
    </script>
    """
    return render_template_string(LAYOUT_TEMPLATE, content=content)

# ================= MARK ATTENDANCE (PUBLIC SCAN NODE) =================
@app.route("/mark/<token>")
def mark(token):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT name,start_time,end_time FROM students WHERE token=?", (token,))
    data = c.fetchone()

    if not data:
        conn.close()
        return """
        <div style="font-family:Arial,sans-serif; text-align:center; padding:50px; background:#0b0f19; min-height:100vh; color:white; box-sizing:border-box;">
            <h2 style="color:#ef4444; margin-top:100px;">Invalid Cryptographic Token</h2>
            <p style="color:#94a3b8;">The AIMCS scanning node returned an unmapped configuration sequence.</p>
        </div>
        """

    name, start_time, end_time = data[0], data[1], data[2]
    now = datetime.utcnow() + timedelta(hours=4)
    start_dt = datetime.strptime(start_time, "%Y-%m-%dT%H:%M")
    end_dt = datetime.strptime(end_time, "%Y-%m-%dT%H:%M")

    if now < start_dt:
        conn.close()
        return f"""
        <div style="font-family:Arial,sans-serif; text-align:center; padding:100px 20px; background-color:#0b0f19; color:#f8fafc; min-height:100vh; box-sizing:border-box;">
            <div style="max-width:500px; margin:0 auto; background-color:#111827; border:1px solid #1e293b; padding:40px; border-radius:20px; box-shadow:0 10px 25px rgba(0,0,0,0.35)">
                <div style="color:#ef4444; font-size:48px; margin-bottom:20px;">🛑</div>
                <h2 style="margin:0 0 10px 0; font-size:24px; font-weight:700;">Validation Window Closed</h2>
                <p style="color:#94a3b8; font-size:14px; margin:0 0 24px 0;">This tracking session has not reached initialized start timelines.</p>
                <div style="background-color:#1e293b; padding:15px; border-radius:12px; font-family:monospace; font-size:13px; color:#3b82f6;">Target Start: {start_dt.strftime('%Y-%m-%d %H:%M')}</div>
            </div>
        </div>
        """

    if now > end_dt:
        conn.close()
        return f"""
        <div style="font-family:Arial,sans-serif; text-align:center; padding:100px 20px; background-color:#0b0f19; color:#f8fafc; min-height:100vh; box-sizing:border-box;">
            <div style="max-width:500px; margin:0 auto; background-color:#111827; border:1px solid #1e293b; padding:40px; border-radius:20px; box-shadow:0 10px 25px rgba(0,0,0,0.35)">
                <div style="color:#ef4444; font-size:48px; margin-bottom:20px;">⚠️</div>
                <h2 style="margin:0 0 10px 0; font-size:24px; font-weight:700;">Validation Link Terminated</h2>
                <p style="color:#94a3b8; font-size:14px; margin:0 0 24px 0;">The processing window bounds for this entity target has fully closed.</p>
                <div style="background-color:#1e293b; padding:15px; border-radius:12px; font-family:monospace; font-size:13px; color:#f43f5e;">Terminated Bound: {end_dt.strftime('%Y-%m-%d %H:%M')}</div>
            </div>
        </div>
        """

    c.execute("SELECT * FROM attendance WHERE name=? AND date(time)=date('now','+4 hours')", (name,))
    if c.fetchone():
        conn.close()
        return f"""
        <div style="font-family:Arial,sans-serif; text-align:center; padding:100px 20px; background-color:#0b0f19; color:#f8fafc; min-height:100vh; box-sizing:border-box;">
            <div style="max-width:500px; margin:0 auto; background-color:#111827; border:1px solid #1e293b; padding:40px; border-radius:20px; box-shadow:0 10px 25px rgba(0,0,0,0.35)">
                <div style="color:#f59e0b; font-size:48px; margin-bottom:20px;">🔁</div>
                <h2 style="margin:0 0 10px 0; font-size:24px; font-weight:700;">Sequence Redundancy</h2>
                <p style="color:#94a3b8; font-size:14px; margin:0 0 10px 0;">Entity ingestion already processed securely.</p>
                <h3 style="color:#f59e0b; margin:0; font-size:18px;">{name} Already Logged</h3>
            </div>
        </div>
        """

    time_str = now.strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO attendance(name,time) VALUES (?,?)", (name,time_str))
    conn.commit()
    conn.close()

    return f"""
    <div style="font-family:Arial,sans-serif; text-align:center; padding:100px 20px; background-color:#0b0f19; color:#f8fafc; min-height:100vh; box-sizing:border-box;">
        <div style="max-width:500px; margin:0 auto; background-color:#111827; border:1px solid #1e293b; padding:40px; border-radius:20px; box-shadow:0 10px 25px rgba(0,0,0,0.35)">
            <div style="color:#10b981; font-size:48px; margin-bottom:20px;">✅</div>
            <h2 style="margin:0 0 10px 0; font-size:24px; font-weight:700; color:#10b981;">Ingestion Verified</h2>
            <p style="color:#94a3b8; font-size:14px; margin:0 0 20px 0;">Attendance successfully saved inside the database array.</p>
            <h3 style="color:#ffffff; margin:0; font-size:20px; font-weight:600; border-top:1px solid #1e293b; padding-top:20px;">{name}</h3>
        </div>
    </div>
    """

# ================= DOWNLOAD EXCEL =================
@app.route("/download")
@login_required
def download():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM attendance", conn)
    conn.close()
    file = "attendance.xlsx"
    df.to_excel(file,index=False)
    return send_file(file,as_attachment=True)

# ================= QR ZIP ARCHIVE =================
@app.route("/download_qrs")
@login_required
def zip_qr():
    z = zipfile.ZipFile("qrs.zip","w")
    if os.path.exists("static/qrs"):
        for f in os.listdir("static/qrs"):
            z.write("static/qrs/"+f)
    z.close()
    return send_file("qrs.zip",as_attachment=True)

# ================= RUN ENGINE =================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
