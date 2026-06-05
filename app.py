from flask import Flask, request, redirect, send_file, render_template_string, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import datetime, timedelta
import secrets
import qrcode
import os
import zipfile
import pandas as pd
import io
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

app = Flask(__name__)
app.secret_key = "supersecretkey"

DB_NAME = "attendance.db"

# ================= DATABASE INITIALIZATION =================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS admin_users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT,
        token TEXT UNIQUE,
        start_time TEXT,
        end_time TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        time TEXT
    )
    """)

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

# ================= PREMIUM MASTER LAYOUT WITH PROFESSIONAL STYLING =================
LAYOUT_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AIMCS | Attendance Management</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <script src="https://cdn.jsdelivr.net/npm/@emailjs/browser@4/dist/email.min.js"></script>
    <script>
        (function(){
            emailjs.init("-oGl3hn1HEMpvxh2T");
        })();
    </script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Inter:wght@300;400;500;600;700&display=swap');
        
        body { 
            font-family: 'Inter', sans-serif; 
            background-color: #0b0f19; 
        }
        .font-brand {
            font-family: 'Plus Jakarta Sans', sans-serif;
        }

        ::-webkit-scrollbar {
            width: 6px;
            height: 6px;
        }
        ::-webkit-scrollbar-track {
            background: #0b0f19;
        }
        ::-webkit-scrollbar-thumb {
            background: #1e293b;
            border-radius: 10px;
        }
        
        /* Custom overrides for the html5-qrcode scanner UI to match premium corporate theme */
        #reader { border: none !important; }
        #reader__dashboard_section_csr button {
            background-color: #3b82f6 !important;
            color: #ffffff !important;
            border: none !important;
            padding: 10px 20px !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            cursor: pointer !important;
            margin: 10px 0 !important;
            font-family: 'Plus Jakarta Sans', sans-serif !important;
            transition: background 0.2s ease;
        }
        #reader__dashboard_section_csr button:hover {
            background-color: #2563eb !important;
        }
        #reader__dashboard_section_swaplink { color: #3b82f6 !important; text-decoration: none !important; font-weight: 500; }
        #reader__scan_region { background: #111827 !important; border-radius: 12px; overflow: hidden; border: 1px solid #1f2937; }
    </style>
</head>
<body class="text-slate-300 min-h-screen flex overflow-x-hidden relative">

    <div class="fixed inset-0 w-screen h-screen pointer-events-none select-none overflow-hidden z-0 opacity-40">
        <div class="absolute -top-[40%] -left-[20%] w-[80rem] h-[80rem] rounded-full bg-gradient-to-tr from-indigo-500/10 to-transparent blur-[120px]"></div>
        <div class="absolute -bottom-[40%] -right-[20%] w-[80rem] h-[80rem] rounded-full bg-gradient-to-bl from-blue-500/5 to-transparent blur-[120px]"></div>
    </div>

    {% if current_user.is_authenticated %}
    <aside class="w-72 bg-[#111827]/90 backdrop-blur-xl border-r border-gray-800/80 flex flex-col fixed h-full z-20">
        <div class="p-6 border-b border-gray-800/80 flex items-center gap-3">
            <div class="bg-gradient-to-br from-indigo-500 to-blue-600 p-2.5 rounded-xl text-white shadow-lg shadow-indigo-500/10">
                <i class="fa-solid fa-layer-group text-lg"></i>
            </div>
            <div>
                <h1 class="text-lg font-bold text-white tracking-tight font-brand">AIMCS Portal</h1>
                <p class="text-[11px] text-slate-400 font-medium uppercase tracking-wider">Enterprise Suite</p>
            </div>
        </div>
        
        <nav class="flex-1 p-4 space-y-1 mt-3">
            <a href="/" class="flex items-center gap-3.5 px-4 py-3 rounded-xl text-sm font-medium transition-all text-slate-400 hover:bg-slate-800/50 hover:text-white">
                <i class="fa-solid fa-house text-base w-5 text-slate-500"></i> Home Gateway
            </a>
            <a href="/dashboard" class="flex items-center gap-3.5 px-4 py-3 rounded-xl text-sm font-medium transition-all text-slate-400 hover:bg-slate-800/50 hover:text-white">
                <i class="fa-solid fa-chart-pie text-base w-5 text-slate-500"></i> Dashboard
            </a>
            <a href="/scanner" class="flex items-center gap-3.5 px-4 py-3 rounded-xl text-sm font-medium transition-all text-blue-400 bg-blue-500/5 border border-blue-500/10 hover:bg-blue-500/10">
                <i class="fa-solid fa-camera text-base w-5 text-blue-400"></i> Live Scanner Kiosk
            </a>
            <a href="/bulk" class="flex items-center gap-3.5 px-4 py-3 rounded-xl text-sm font-medium transition-all text-slate-400 hover:bg-slate-800/50 hover:text-white">
                <i class="fa-solid fa-qrcode text-base w-5 text-slate-500"></i> Create QR Codes
            </a>
            <a href="/analysis" class="flex items-center gap-3.5 px-4 py-3 rounded-xl text-sm font-medium transition-all text-slate-400 hover:bg-slate-800/50 hover:text-white">
                <i class="fa-solid fa-chart-line text-base w-5 text-slate-500"></i> Analytics
            </a>
            <a href="/profile" class="flex items-center gap-3.5 px-4 py-3 rounded-xl text-sm font-medium transition-all text-slate-400 hover:bg-slate-800/50 hover:text-white">
                <i class="fa-solid fa-shield-halved text-base w-5 text-slate-500"></i> Security Settings
            </a>
            <a href="/logout" class="flex items-center gap-3.5 px-4 py-3 rounded-xl text-sm font-medium transition-all text-rose-400 hover:bg-rose-500/5 hover:text-rose-300">
                <i class="fa-solid fa-right-from-bracket text-base w-5"></i> Logout
            </a>
        </nav>

        <div class="p-4 border-t border-gray-800/80">
            <div class="bg-gray-900/60 p-4 rounded-xl border border-gray-800/50 flex items-center gap-3">
                <div class="w-9 h-9 rounded-full bg-slate-800 text-slate-200 flex items-center justify-center font-bold text-sm border border-slate-700">
                    {{ current_user.username[0].upper() }}
                </div>
                <div class="truncate">
                    <p class="text-xs font-semibold text-white truncate font-brand">{{ current_user.username }}</p>
                    <p class="text-[10px] text-emerald-400 truncate font-medium flex items-center gap-1">
                        <span class="h-1 w-1 rounded-full bg-emerald-400"></span> Management Node
                    </p>
                </div>
            </div>
        </div>
    </aside>
    {% endif %}

    <main class="flex-1 {% if current_user.is_authenticated %}pl-72{% endif %} min-h-screen flex flex-col relative z-10">
        <header id="mainHeader" class="h-20 bg-[#0b0f19]/70 backdrop-blur-xl border-b border-gray-800/60 flex items-center justify-between px-8 sticky top-0 z-30">
            <div class="flex items-center gap-2">
                <span class="h-2 w-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]"></span>
                <p class="text-xs font-semibold tracking-wider text-slate-400 uppercase font-brand">System Integrity Nominal</p>
            </div>
            <div class="text-xs font-medium text-slate-400 bg-gray-900/80 px-4 py-2 rounded-xl border border-gray-800/80 shadow-sm">
                <i class="fa-regular fa-clock mr-2 text-indigo-400"></i> <span id="liveClock" class="font-mono text-slate-300"></span>
            </div>
        </header>

        <div class="p-8 flex-1 flex flex-col justify-start max-w-6xl w-full mx-auto relative">
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

# ================= LIVE SCANNER CONTINUOUS TAP KIOSK =================
@app.route("/scanner")
@login_required
def scanner():
    content = """
    <div class="max-w-2xl mx-auto space-y-6 w-full">
        <div class="text-center">
            <h2 class="text-2xl font-bold text-white tracking-tight font-brand">Live Kiosk Scanner</h2>
            <p class="text-sm text-slate-400 mt-1">Position a tokenized identity QR matrix near the optical frame sensor.</p>
        </div>
        
        <div class="bg-[#111827]/80 backdrop-blur-xl border border-gray-800/80 rounded-2xl p-6 shadow-xl relative">
            
            <div class="absolute inset-0 border border-blue-500/20 rounded-2xl m-6 pointer-events-none z-10">
                <div class="absolute top-0 left-0 w-6 h-6 border-t-2 border-l-2 border-blue-500/70"></div>
                <div class="absolute top-0 right-0 w-6 h-6 border-t-2 border-r-2 border-blue-500/70"></div>
                <div class="absolute bottom-0 left-0 w-6 h-6 border-b-2 border-l-2 border-blue-500/70"></div>
                <div class="absolute bottom-0 right-0 w-6 h-6 border-b-2 border-r-2 border-blue-500/70"></div>
            </div>

            <div id="reader" class="w-full rounded-xl overflow-hidden relative z-0 min-h-[300px] flex items-center justify-center bg-gray-950"></div>
            
            <div id="scanResult" class="hidden mt-4 p-4 rounded-xl text-center font-semibold text-sm shadow-sm transition-all duration-300"></div>
        </div>

        <script src="https://unpkg.com/html5-qrcode"></script>
        <script>
            let html5QrcodeScanner;
            
            function onScanSuccess(decodedText, decodedResult) {
                html5QrcodeScanner.pause();
                
                let token = '';
                try {
                    token = decodedText.split('/mark/')[1];
                } catch(e) {}

                if (!token) {
                    showResult("Unrecognized QR Code Format", "error");
                    setTimeout(() => html5QrcodeScanner.resume(), 2500);
                    return;
                }

                fetch('/api/mark/' + token)
                    .then(res => res.json())
                    .then(data => {
                        showResult(data.message, data.status);
                        setTimeout(() => {
                            document.getElementById('scanResult').classList.add('hidden');
                            html5QrcodeScanner.resume();
                        }, 2500); 
                    })
                    .catch(err => {
                        showResult("Network Transmission Error", "error");
                        setTimeout(() => html5QrcodeScanner.resume(), 2500);
                    });
            }

            function showResult(msg, type) {
                const resDiv = document.getElementById('scanResult');
                resDiv.classList.remove('hidden', 'bg-emerald-500/5', 'text-emerald-400', 'bg-rose-500/5', 'text-rose-400', 'bg-blue-500/5', 'text-blue-400', 'border-emerald-500/20', 'border-rose-500/20', 'border-blue-500/20');
                
                if (type === 'success') {
                    resDiv.classList.add('bg-emerald-500/5', 'text-emerald-400', 'border', 'border-emerald-500/20');
                    resDiv.innerHTML = `<i class="fa-solid fa-circle-check text-lg mr-2 align-middle"></i> <span class="font-brand tracking-wide">${msg}</span>`;
                } else if (type === 'error') {
                    resDiv.classList.add('bg-rose-500/5', 'text-rose-400', 'border', 'border-rose-500/20');
                    resDiv.innerHTML = `<i class="fa-solid fa-circle-xmark text-lg mr-2 align-middle"></i> <span class="font-brand tracking-wide">${msg}</span>`;
                } else {
                    resDiv.classList.add('bg-blue-500/5', 'text-blue-400', 'border', 'border-blue-500/20');
                    resDiv.innerHTML = `<i class="fa-solid fa-triangle-exclamation text-lg mr-2 align-middle"></i> <span class="font-brand tracking-wide">${msg}</span>`;
                }
            }

            document.addEventListener("DOMContentLoaded", () => {
                html5QrcodeScanner = new Html5QrcodeScanner(
                    "reader",
                    { fps: 15, qrbox: {width: 250, height: 250} },
                    false);
                html5QrcodeScanner.render(onScanSuccess);
            });
        </script>
    </div>
    """
    return render_template_string(LAYOUT_TEMPLATE, content=content)

# ================= BACKGROUND API FOR CONTINUOUS SCANNING =================
@app.route("/api/mark/<token>")
def api_mark(token):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT name,start_time,end_time FROM students WHERE token=?", (token,))
    data = c.fetchone()

    if not data:
        conn.close()
        return jsonify({"status": "error", "message": "Invalid Link Identifier"})

    name, start_time, end_time = data
    now = datetime.utcnow() + timedelta(hours=4)
    start_dt = datetime.strptime(start_time, "%Y-%m-%dT%H:%M")
    end_dt = datetime.strptime(end_time, "%Y-%m-%dT%H:%M")

    if now < start_dt:
        conn.close()
        return jsonify({"status": "warning", "message": f"Sealed: {name} (Starts {start_time})"})

    if now > end_dt:
        conn.close()
        return jsonify({"status": "error", "message": f"Expired: {name}"})

    c.execute("SELECT * FROM attendance WHERE name=? AND date(time)=date('now','+4 hours')", (name,))
    if c.fetchone():
        conn.close()
        return jsonify({"status": "warning", "message": f"Already Logged: {name}"})

    time_str = now.strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO attendance(name,time) VALUES (?,?)", (name,time_str))
    conn.commit()
    conn.close()

    return jsonify({"status": "success", "message": f"Verified: {name}"})

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
            error_msg = "Invalid credentials. Integration refused."

    content = f"""
    <div class="relative z-20 max-w-md w-full mx-auto my-auto bg-[#111827]/80 backdrop-blur-xl border border-gray-800 rounded-2xl p-8 space-y-6 shadow-2xl">
        <div class="text-center space-y-2">
            <div class="inline-flex p-3 bg-gray-900 border border-gray-800 text-indigo-400 rounded-xl mb-1">
                <i class="fa-solid fa-shield text-xl"></i>
            </div>
            <h2 class="text-xl font-bold text-white tracking-tight font-brand">Administrative Node Gateway</h2>
            <p class="text-xs text-slate-400">Provide authoritative parameters to access management network.</p>
        </div>
        
        {f'<div class="p-3 bg-rose-500/5 border border-rose-500/20 text-rose-400 text-xs rounded-xl font-medium text-center">{error_msg}</div>' if error_msg else ''}

        <form method="POST" class="space-y-4">
            <div class="space-y-1.5">
                <label class="text-[11px] font-semibold text-slate-400 uppercase tracking-wider font-brand">Username</label>
                <input type="text" name="username" class="w-full bg-gray-900/50 border border-gray-800 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-indigo-500/50 transition-colors" placeholder="Admin username" required>
            </div>
            <div class="space-y-1.5">
                <label class="text-[11px] font-semibold text-slate-400 uppercase tracking-wider font-brand">Password</label>
                <input type="password" name="password" class="w-full bg-gray-900/50 border border-gray-800 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-indigo-500/50 transition-colors" placeholder="Password security key" required>
            </div>
            <button type="submit" class="w-full inline-flex items-center justify-center px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold rounded-xl text-sm transition-all shadow-md shadow-indigo-600/10">
                Authenticate Secure Session
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

# ================= SECURITY SETTINGS =================
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
            status_msg = """<div class="p-3 bg-emerald-500/5 border border-emerald-500/20 text-emerald-400 text-xs rounded-xl font-medium text-center">Password signature successfully modulated.</div>"""
        else:
            status_msg = """<div class="p-3 bg-rose-500/5 border border-rose-500/20 text-rose-400 text-xs rounded-xl font-medium text-center">Current operational security key verification failed.</div>"""
        conn.close()

    content = f"""
    <div class="max-w-xl mx-auto bg-[#111827]/80 backdrop-blur-md border border-gray-800 rounded-2xl p-8 space-y-6 shadow-xl">
        <div class="border-b border-gray-800 pb-3">
            <h2 class="text-lg font-bold text-white tracking-tight font-brand">Update Authorization Token</h2>
            <p class="text-xs text-slate-400 mt-0.5">Revoke old credentials and initialize modified structural parameters.</p>
        </div>

        {status_msg}

        <form method="POST" class="space-y-4">
            <div class="space-y-1.5">
                <label class="text-xs font-semibold text-slate-400 uppercase tracking-wider font-brand">Current Password Matrix</label>
                <input type="password" name="old_password" class="w-full bg-gray-900 border border-gray-800 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-indigo-500/50 transition-colors" required>
            </div>
            <div class="space-y-1.5">
                <label class="text-xs font-semibold text-slate-400 uppercase tracking-wider font-brand">New Configuration Password</label>
                <input type="password" name="new_password" class="w-full bg-gray-900 border border-gray-800 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-indigo-500/50 transition-colors" required>
            </div>
            <button type="submit" class="w-full inline-flex items-center justify-center px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold rounded-xl text-sm transition-all shadow-md">
                Commit Structural Modification
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
    <div class="w-full max-w-4xl mx-auto mt-12">
        <div class="relative w-full rounded-2xl overflow-hidden border border-gray-800/80 bg-[#111827]/80 backdrop-blur-xl shadow-2xl p-12 md:p-16">
            
            <div class="relative z-20 max-w-xl space-y-6">
                <div class="space-y-2">
                    <div class="inline-flex px-3 py-1 bg-indigo-500/10 border border-indigo-500/20 rounded-full text-[11px] font-semibold tracking-wide text-indigo-400 uppercase font-brand">
                        Operational Framework Core
                    </div>
                    <h2 class="text-4xl md:text-5xl font-extrabold text-white tracking-tight font-brand leading-tight">
                        AIMCS Attendance Optimization System
                    </h2>
                </div>
                
                <p class="text-sm text-slate-400 leading-relaxed font-normal border-l-2 border-slate-700 pl-4">
                    Deploy cryptographically isolated identity matrices, orchestrate localized telemetric scans, and archive automated real-time verification logs inside a highly-secure architectural framework.
                </p>
                
                <div class="pt-2 flex flex-wrap gap-3">
                    <a href="/dashboard" class="inline-flex items-center justify-center px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-xl transition-all shadow-md shadow-indigo-600/10">
                        Open Management Node <i class="fa-solid fa-arrow-right ml-2 text-[10px]"></i>
                    </a>
                    <a href="/scanner" class="inline-flex items-center justify-center px-5 py-2.5 bg-gray-900 hover:bg-gray-800 text-slate-300 text-xs font-semibold rounded-xl transition-all border border-gray-800 shadow-sm">
                        <i class="fa-solid fa-video mr-2 text-[11px] text-indigo-400"></i> Initialize Optical Scanner
                    </a>
                </div>
            </div>
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
    <div class="space-y-6 w-full max-w-4xl mx-auto">
        <div>
            <h2 class="text-2xl font-bold text-white tracking-tight font-brand">System Telemetry Dashboard</h2>
            <p class="text-xs text-slate-400 mt-0.5">High-level operational index pipeline and tactical instrumentation parameters.</p>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-5">
            <div class="bg-[#111827]/80 backdrop-blur-md border border-gray-800/80 p-6 rounded-2xl flex items-center justify-between shadow-sm hover:border-slate-700 transition-colors">
                <div class="space-y-1">
                    <p class="text-xs font-semibold uppercase tracking-wider text-slate-400 font-brand">Registered Directives</p>
                    <h3 class="text-3xl font-bold text-white font-brand tracking-tight">{students}</h3>
                </div>
                <div class="h-10 w-10 bg-gray-900 border border-gray-800 text-indigo-400 rounded-xl flex items-center justify-center text-sm shadow-inner">
                    <i class="fa-solid fa-address-book"></i>
                </div>
            </div>

            <div class="bg-[#111827]/80 backdrop-blur-md border border-gray-800/80 p-6 rounded-2xl flex items-center justify-between shadow-sm hover:border-slate-700 transition-colors">
                <div class="space-y-1">
                    <p class="text-xs font-semibold uppercase tracking-wider text-slate-400 font-brand">Synchronized Scans</p>
                    <h3 class="text-3xl font-bold text-white font-brand tracking-tight">{attendance}</h3>
                </div>
                <div class="h-10 w-10 bg-gray-900 border border-gray-800 text-blue-400 rounded-xl flex items-center justify-center text-sm shadow-inner">
                    <i class="fa-solid fa-fingerprint"></i>
                </div>
            </div>

            <div class="bg-[#111827]/80 backdrop-blur-md border border-gray-800/80 p-6 rounded-2xl flex items-center justify-between shadow-sm hover:border-emerald-500/20 transition-colors">
                <div class="space-y-1">
                    <p class="text-xs font-semibold uppercase tracking-wider text-slate-400 font-brand">Server Cluster Core</p>
                    <h3 class="text-sm font-bold text-emerald-400 font-brand mt-1.5 flex items-center gap-1.5">
                        <span class="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse"></span> Fully Operational
                    </h3>
                </div>
                <div class="h-10 w-10 bg-emerald-500/5 border border-emerald-500/10 text-emerald-400 rounded-xl flex items-center justify-center text-sm shadow-inner">
                    <i class="fa-solid fa-network-wired"></i>
                </div>
            </div>
        </div>

        <div class="bg-[#111827]/80 backdrop-blur-md border border-gray-800/80 rounded-2xl p-6 shadow-sm">
            <h3 class="text-xs font-bold text-slate-400 mb-4 uppercase tracking-wider font-brand">Deployment Matrix Operations</h3>
            <div class="grid grid-cols-1 sm:grid-cols-4 gap-4">
                <a href="/scanner" class="flex flex-col items-center justify-center p-5 bg-gray-900/40 hover:bg-indigo-500/5 hover:border-indigo-500/30 rounded-xl border border-gray-800 text-center group transition-all">
                    <i class="fa-solid fa-expand text-lg text-slate-400 mb-2 group-hover:text-indigo-400 transition-colors"></i>
                    <span class="text-xs font-semibold text-slate-300 group-hover:text-white transition-colors">Launch Optical Kiosk</span>
                </a>
                <a href="/bulk" class="flex flex-col items-center justify-center p-5 bg-gray-900/40 hover:bg-indigo-500/5 hover:border-indigo-500/30 rounded-xl border border-gray-800 text-center group transition-all">
                    <i class="fa-solid fa-qrcode text-lg text-slate-400 mb-2 group-hover:text-indigo-400 transition-colors"></i>
                    <span class="text-xs font-semibold text-slate-300 group-hover:text-white transition-colors">Generate Batch Identifiers</span>
                </a>
                <a href="/download" class="flex flex-col items-center justify-center p-5 bg-gray-900/40 hover:bg-indigo-500/5 hover:border-indigo-500/30 rounded-xl border border-gray-800 text-center group transition-all">
                    <i class="fa-solid fa-file-invoice text-lg text-slate-400 mb-2 group-hover:text-indigo-400 transition-colors"></i>
                    <span class="text-xs font-semibold text-slate-300 group-hover:text-white transition-colors">Export Telemetry Ledger</span>
                </a>
                <a href="/download_qrs" class="flex flex-col items-center justify-center p-5 bg-gray-900/40 hover:bg-indigo-500/5 hover:border-indigo-500/30 rounded-xl border border-gray-800 text-center group transition-all">
                    <i class="fa-solid fa-box-archive text-lg text-slate-400 mb-2 group-hover:text-indigo-400 transition-colors"></i>
                    <span class="text-xs font-semibold text-slate-300 group-hover:text-white transition-colors">Download Matrix Assets</span>
                </a>
            </div>
        </div>
    </div>
    """
    return render_template_string(LAYOUT_TEMPLATE, content=content)

# ================= BULK QR GENERATION =================
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
                print("Error logging row item:", e)

        conn.commit()
        conn.close()

        js_data = "\n".join(js_students)

        content = f"""
        <div class="max-w-xl mx-auto bg-[#111827]/80 backdrop-blur-md border border-gray-800 rounded-2xl p-8 text-center space-y-5 shadow-xl">
            <div class="inline-flex p-3 bg-emerald-500/10 text-emerald-400 rounded-full border border-emerald-500/20">
                <i class="fa-solid fa-circle-check text-2xl"></i>
            </div>
            <h2 class="text-xl font-bold text-white tracking-tight font-brand">Batch Modulated Safely</h2>
            <p class="text-slate-400 text-sm max-w-sm mx-auto leading-relaxed">
                Tokens successfully engineered for <span class="text-indigo-400 font-semibold">{success}</span> corporate nodes. Structural distribution ongoing via centralized relay pipelines.
            </p>

            <script>
            const students = `{js_data}`.trim().split('\\n');
            students.forEach(s => {{
                let p = s.split(",");
                if (p.length < 4) return;
                let name = p[0];
                let email = p[1];
                let link = p[2];
                let qr_image = p[3];

                emailjs.send(
                    "service_iuneir8",
                    "template_uyhe7xo",
                    {{
                        name: name,
                        email: email,
                        qr_link: link,
                        qr_image: qr_image
                    }}
                ).then(
                    function(response) {{
                        console.log("Email dispatch complete for " + email, response.status, response.text);
                    }},
                    function(error) {{
                        console.error("Email delivery aborted for " + email, error);
                    }}
                );
            }});
            </script>

            <div class="pt-4 border-t border-gray-800">
                <a href='/dashboard' class="inline-flex items-center justify-center px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-xl transition-all shadow-md">
                    Return to Operational Base
                </a>
            </div>
        </div>
        """
        return render_template_string(LAYOUT_TEMPLATE, content=content)

    content = """
    <div class="max-w-2xl mx-auto bg-[#111827]/80 backdrop-blur-md border border-gray-800 rounded-2xl p-8 space-y-6 shadow-md">
        <div class="border-b border-gray-800 pb-3">
            <h2 class="text-xl font-bold text-white tracking-tight font-brand">Engineering Structural QR Vectors</h2>
            <p class="text-xs text-slate-400 mt-1">Configure chronological perimeter parameters and directory listings.</p>
        </div>

        <form method='POST' class="space-y-5">
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div class="space-y-1.5">
                    <label class='text-[11px] font-semibold text-slate-400 uppercase tracking-wider font-brand'>Validation Horizon Start</label>
                    <input type='datetime-local' name='start_time' class='w-full bg-gray-900 border border-gray-800 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-indigo-500/50 transition-colors' required>
                </div>
                <div class="space-y-1.5">
                    <label class='text-[11px] font-semibold text-slate-400 uppercase tracking-wider font-brand'>Validation Horizon End</label>
                    <input type='datetime-local' name='end_time' class='w-full bg-gray-900 border border-gray-800 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-indigo-500/50 transition-colors' required>
                </div>
            </div>

            <div class="space-y-1.5">
                <label class='text-[11px] font-semibold text-slate-400 uppercase tracking-wider font-brand'>Corporate Entity Directories (Syntax: Name, Email Address)</label>
                <textarea name='data' class='w-full h-40 bg-gray-900 border border-gray-800 rounded-xl p-4 text-xs text-white focus:outline-none focus:border-indigo-500/50 transition-colors font-mono' placeholder="Alice Smith, alice@organization.com&#10;Bob Jones, bob@organization.com" required></textarea>
                <p class="text-[11px] text-slate-500 italic mt-1">Isolate sequential records using unified line-breaks and comma-demarcations.</p>
            </div>
            
            <button type='submit' class="w-full inline-flex items-center justify-center px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold rounded-xl text-sm shadow-md transition-all">
                Publish Identifiers & Broadcast Matrices
            </button>
        </form>
    </div>
    """
    return render_template_string(LAYOUT_TEMPLATE, content=content)

# ================= ANALYTICS & REPORTS =================
@app.route("/analysis")
@login_required
def analysis():
    conn = sqlite3.connect(DB_NAME)
    df_logs = pd.read_sql_query("SELECT * FROM attendance ORDER BY time DESC", conn)
    df_config = pd.read_sql_query("SELECT name, start_time, end_time FROM students", conn)
    conn.close()

    chart_url = ""
    if not df_logs.empty:
        try:
            df_logs['date_only'] = df_logs['time'].apply(lambda x: x.split()[0] if x else '')
            attendance_counts = df_logs.groupby('date_only').size()

            plt.figure(figsize=(7, 3))
            plt.gcf().patch.set_facecolor('#111827')
            plt.gcf().patch.set_alpha(0.0)
            ax = plt.gca()
            ax.set_facecolor('#111827')
            ax.patch.set_alpha(0.0)
            
            # Professionally colored indigo bars matching corporate tone
            attendance_counts.plot(kind='bar', color='#4f46e5', width=0.35, ax=ax)
            
            ax.tick_params(colors='#94a3b8', labelsize=8)
            ax.spines['bottom'].set_color('#334155')
            ax.spines['left'].set_color('#334155')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.grid(axis='y', color='#334155', linestyle='--', alpha=0.1)
            
            plt.title("Synchronized Time-Series Indexes", color='white', fontsize=11, pad=10, weight='semibold', fontname='sans-serif')
            plt.tight_layout()
            
            img_buf = io.BytesIO()
            plt.savefig(img_buf, format='png', transparent=True, bbox_inches='tight')
            img_buf.seek(0)
            import base64
            chart_url = "data:image/png;base64," + base64.b64encode(img_buf.getvalue()).decode('utf-8')
            plt.close()
        except Exception as e:
            print("Chart configuration logged error:", e)

    table_rows = ""
    if not df_logs.empty:
        for idx, row in df_logs.iterrows():
            table_rows += f"""
            <tr class="border-b border-gray-800/60 text-slate-300 text-xs hover:bg-slate-800/30 transition-colors">
                <td class="px-5 py-3 font-mono text-slate-500">#{row['id']}</td>
                <td class="px-5 py-3 font-medium text-white">{row['name']}</td>
                <td class="px-5 py-3 font-mono text-slate-400">{row['time']}</td>
                <td class="px-5 py-3"><span class="px-2 py-0.5 bg-emerald-500/5 border border-emerald-500/20 text-emerald-400 rounded-full text-[10px] font-semibold tracking-wide">VERIFIED</span></td>
            </tr>
            """
    else:
        table_rows = """
        <tr>
            <td colspan="4" class="px-5 py-10 text-center text-xs text-slate-500">No telemetry data logs mapped within storage array.</td>
        </tr>
        """

    content = f"""
    <div class="space-y-6 w-full max-w-4xl mx-auto">
        <div>
            <h2 class="text-2xl font-bold text-white tracking-tight font-brand">Statistical Metrics Analysis</h2>
            <p class="text-xs text-slate-400 mt-0.5">Track system integration indexes, authoritative identity matrices, and physical authorization endpoints.</p>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-3 gap-5">
            <div class="lg:col-span-1 bg-[#111827]/80 backdrop-blur-md border border-gray-800 rounded-2xl p-4 flex flex-col justify-center items-center shadow-sm">
                {f'<img src="{chart_url}" class="w-full" />' if chart_url else '<div class="text-slate-500 text-xs text-center py-12">Insufficient quantitative array metrics to draw statistical vector graph.</div>'}
            </div>
            
            <div class="lg:col-span-2 bg-[#111827]/80 backdrop-blur-md border border-gray-800 rounded-2xl p-5 space-y-3 shadow-sm">
                <h3 class="text-xs font-bold text-slate-400 uppercase tracking-wider font-brand">Active Authorization Matrix Directory</h3>
                <div class="overflow-x-auto border border-gray-800/60 rounded-xl bg-gray-900/20">
                    <table class="w-full text-left border-collapse">
                        <thead>
                            <tr class="bg-gray-900 border-b border-gray-800 text-[10px] font-semibold text-indigo-400 uppercase tracking-wider">
                                <th class="px-5 py-2.5">Index ID</th>
                                <th class="px-5 py-2.5">Node Label</th>
                                <th class="px-5 py-2.5">Active Authorization Horizon Limits</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-gray-800/40 text-xs text-slate-300">
                            {"".join([f'<tr class="hover:bg-slate-800/30 transition-colors"><td class="px-5 py-2.5 font-mono text-slate-500">#{i+1}</td><td class="px-5 py-2.5 font-medium text-white">{r["name"]}</td><td class="px-5 py-2.5 font-mono text-slate-400 text-[11px]">{r["start_time"]} ➔ {r["end_time"]}</td></tr>' for i, r in df_config.iterrows()]) if not df_config.empty else '<tr><td colspan="3" class="px-5 py-5 text-center text-slate-500">No structural parameters defined yet.</td></tr>'}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <div class="bg-[#111827]/80 backdrop-blur-md border border-gray-800 rounded-2xl p-5 shadow-sm">
            <h3 class="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 font-brand">Real-Time Sync Telemetry Pipeline</h3>
            <div class="overflow-hidden border border-gray-800 rounded-xl bg-gray-900/20">
                <div class="max-h-64 overflow-y-auto">
                    <table class="w-full text-left border-collapse">
                        <thead class="sticky top-0 bg-gray-900 border-b border-gray-800 text-[10px] font-semibold text-indigo-400 uppercase tracking-wider z-10">
                            <tr>
                                <th class="px-5 py-2.5">Log Segment ID</th>
                                <th class="px-5 py-2.5">Associated Identity Label</th>
                                <th class="px-5 py-2.5">Telemetric Stamp</th>
                                <th class="px-5 py-2.5">Verification Signature</th>
                            </tr>
                        </thead>
                        <tbody>
                            {table_rows}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
    """
    return render_template_string(LAYOUT_TEMPLATE, content=content)

# ================= PUBLIC MARK ATTENDANCE SCREEN (FOR STUDENTS) =================
@app.route("/mark/<token>")
def mark(token):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
    SELECT name,start_time,end_time
    FROM students
    WHERE token=?
    """, (token,))

    data = c.fetchone()

    PAGE_BODY_STYLE = """
    font-family: 'Inter', system-ui, -apple-system, sans-serif; 
    text-align: center; 
    padding: 80px 16px; 
    background-color: #0b0f19; 
    color: #f8fafc; 
    min-height: 100vh; 
    box-sizing: border-box; 
    display: flex; 
    align-items: center; 
    justify-content: center;
    """
    
    PANEL_CARD_STYLE = """
    max-width: 440px; 
    width: 100%; 
    background-color: #111827; 
    border: 1px solid #1f2937; 
    padding: 40px 32px; 
    border-radius: 16px; 
    box-shadow: 0 10px 25px -5px rgba(0,0,0,0.3);
    """

    if not data:
        conn.close()
        return f"""
        <div style="{PAGE_BODY_STYLE}">
            <div style="{PANEL_CARD_STYLE}">
                <div style="color:#ef4444; font-size:36px; margin-bottom:16px;">✕</div>
                <h2 style="margin:0 0 6px 0; font-size:18px; font-weight:700; font-family:'Plus Jakarta Sans',sans-serif;">Invalid Identity Token Reference</h2>
                <p style="color:#94a3b8; font-size:13px; line-height:1.6; margin:0;">The credential verification matrix queried does not map to an authoritative configuration node or has been permanently purged.</p>
            </div>
        </div>
        """

    name = data[0]
    start_time = data[1]
    end_time = data[2]

    now = datetime.utcnow() + timedelta(hours=4)

    start_dt = datetime.strptime(start_time, "%Y-%m-%dT%H:%M")
    end_dt = datetime.strptime(end_time, "%Y-%m-%dT%H:%M")

    if now < start_dt:
        conn.close()
        return f"""
        <div style="{PAGE_BODY_STYLE}">
            <div style="{PANEL_CARD_STYLE}">
                <div style="color:#6366f1; font-size:36px; margin-bottom:16px;">🔒</div>
                <h2 style="margin:0 0 6px 0; font-size:18px; font-weight:700; font-family:'Plus Jakarta Sans',sans-serif;">Telemetric Transmission Sealed</h2>
                <p style="color:#94a3b8; font-size:13px; margin:0 0 20px 0; line-height:1.6;">This verification authorization window has not initialized operational capability yet.</p>
                <div style="background-color:#1f2937; padding:12px; border-radius:10px; font-family:monospace; font-size:12px; color:#94a3b8; border:1px solid #374151;">
                    Scheduled Unlock Time: <br/><strong style="font-size:13px; color:#6366f1; display:block; margin-top:6px;">{start_dt.strftime('%Y-%m-%d %H:%M')}</strong>
                </div>
            </div>
        </div>
        """

    if now > end_dt:
        conn.close()
        return f"""
        <div style="{PAGE_BODY_STYLE}">
            <div style="{PANEL_CARD_STYLE}">
                <div style="color:#94a3b8; font-size:36px; margin-bottom:16px;">⚠️</div>
                <h2 style="margin:0 0 6px 0; font-size:18px; font-weight:700; font-family:'Plus Jakarta Sans',sans-serif;">Verification Window Terminated</h2>
                <p style="color:#94a3b8; font-size:13px; margin:0 0 20px 0; line-height:1.6;">The chronologically assigned parameters defining this telemetry lock have systematically elapsed.</p>
                <div style="background-color:#1f2937; padding:12px; border-radius:10px; font-family:monospace; font-size:12px; color:#f43f5e; border:1px solid #374151;">
                    Lifecycle Expiry Logged At: <br/><strong style="font-size:13px; color:#ffffff; display:block; margin-top:6px;">{end_dt.strftime('%Y-%m-%d %H:%M')}</strong>
                </div>
            </div>
        </div>
        """

    c.execute("""
    SELECT *
    FROM attendance
    WHERE name=?
    AND date(time)=date('now','+4 hours')
    """, (name,))

    if c.fetchone():
        conn.close()
        return f"""
        <div style="{PAGE_BODY_STYLE}">
            <div style="{PANEL_CARD_STYLE}">
                <div style="color:#3b82f6; font-size:36px; margin-bottom:16px;">🛡️</div>
                <h2 style="margin:0 0 6px 0; font-size:18px; font-weight:700; font-family:'Plus Jakarta Sans',sans-serif;">Telemetry Signature Redundant</h2>
                <p style="color:#94a3b8; font-size:13px; margin:0 0 16px 0; line-height:1.6;">Your explicit metric allocation inside this 24-hour block has already been successfully committed.</p>
                <div style="border-top:1px solid #273142; padding-top:16px;">
                    <h3 style="color:#ffffff; margin:0; font-size:15px; font-weight:600;">{name}</h3>
                    <p style="color:#3b82f6; font-size:10px; text-transform:uppercase; font-weight:bold; margin-top:4px; letter-spacing:1px;">Verification Status: Confirmed</p>
                </div>
            </div>
        </div>
        """

    time_str = now.strftime("%Y-%m-%d %H:%M:%S")

    c.execute("""
    INSERT INTO attendance(name,time)
    VALUES (?,?)
    """, (name,time_str))

    conn.commit()
    conn.close()

    return f"""
    <div style="{PAGE_BODY_STYLE}">
        <div style="{PANEL_CARD_STYLE}">
            <div style="color:#10b981; font-size:36px; margin-bottom:16px;">✓</div>
            <h2 style="margin:0 0 6px 0; font-size:18px; font-weight:700; color:#10b981; font-family:'Plus Jakarta Sans',sans-serif;">Telemetry Log Sequenced</h2>
            <p style="color:#94a3b8; font-size:13px; margin:0 0 20px 0; line-height:1.6;">Operational attendance data successfully mapped to the master database node pipeline logs.</p>
            <div style="background:rgba(16,185,129,0.02); border:1px solid rgba(16,185,129,0.15); padding:16px; border-radius:10px;">
                <h3 style="color:#ffffff; margin:0; font-size:15px; font-weight:600;">{name}</h3>
                <p style="color:#10b981; font-family:monospace; margin-top:4px; font-size:11px; font-weight:500;">{time_str}</p>
            </div>
        </div>
    </div>
    """

# ================= DATA DOWNLOAD EXPORTS =================
@app.route("/download")
@login_required
def download():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM attendance", conn)
    conn.close()

    file = "attendance.xlsx"
    df.to_excel(file, index=False)
    return send_file(file, as_attachment=True)

@app.route("/download_qrs")
@login_required
def zip_qr():
    z = zipfile.ZipFile("qrs.zip", "w")
    if os.path.exists("static/qrs"):
        for f in os.listdir("static/qrs"):
            z.write("static/qrs/" + f)
    z.close()
    return send_file("qrs.zip", as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
