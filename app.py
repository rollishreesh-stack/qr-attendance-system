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

# ================= PREMIUM MASTER LAYOUT WITH GOLD KINETIC WALLPAPER =================
LAYOUT_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AIMCS | Attendance System</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <script src="https://cdn.jsdelivr.net/npm/@emailjs/browser@4/dist/email.min.js"></script>
    <script>
        (function(){
            emailjs.init("-oGl3hn1HEMpvxh2T");
        })();
    </script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;600;800;900&display=swap');
        
        body { 
            font-family: 'Inter', sans-serif; 
            background-color: #030712; 
        }
        .font-outfit {
            font-family: 'Outfit', sans-serif;
        }

        @keyframes streamLeft {
            0% { transform: translate3d(0, 0, 0); }
            100% { transform: translate3d(-50%, 0, 0); }
        }
        @keyframes streamRight {
            0% { transform: translate3d(-50%, 0, 0); }
            100% { transform: translate3d(0, 0, 0); }
        }

        .kinetic-track-left {
            display: flex;
            width: max-content;
            animation: streamLeft 32s linear infinite;
        }
        .kinetic-track-right {
            display: flex;
            width: max-content;
            animation: streamRight 38s linear infinite;
        }
        .motion-center-glow {
            animation: subtlePulse 4s ease-in-out infinite;
        }
        @keyframes subtlePulse {
            0%, 100% { opacity: 0.1; transform: scale(0.98); }
            50% { opacity: 0.3; transform: scale(1.02); }
        }

        ::-webkit-scrollbar {
            width: 6px;
            height: 6px;
        }
        ::-webkit-scrollbar-track {
            background: #030712;
        }
        ::-webkit-scrollbar-thumb {
            background: #1e293b;
            border-radius: 10px;
        }
        
        /* Custom overrides for the html5-qrcode scanner UI to match dark theme */
        #reader { border: none !important; }
        #reader__dashboard_section_csr button {
            background-color: #f59e0b !important;
            color: #030712 !important;
            border: none !important;
            padding: 8px 16px !important;
            border-radius: 8px !important;
            font-weight: bold !important;
            cursor: pointer !important;
            margin: 10px 0 !important;
            font-family: 'Outfit', sans-serif !important;
        }
        #reader__dashboard_section_swaplink { color: #f59e0b !important; text-decoration: none !important; }
        #reader__scan_region { background: #0b0f19 !important; border-radius: 12px; overflow: hidden; }
    </style>
</head>
<body class="text-slate-300 min-h-screen flex overflow-x-hidden relative">

    <div class="fixed inset-0 w-screen h-screen pointer-events-none select-none overflow-hidden z-0 flex flex-col justify-between py-8 opacity-40">
        <div class="w-full overflow-hidden whitespace-nowrap text-[8.5rem] font-black font-outfit uppercase tracking-[1.5rem] text-amber-500/30">
            <div class="kinetic-track-left">
                <span>AIMCS&nbsp;AIMCS&nbsp;AIMCS&nbsp;AIMCS&nbsp;AIMCS&nbsp;AIMCS&nbsp;AIMCS&nbsp;AIMCS&nbsp;</span>
                <span>AIMCS&nbsp;AIMCS&nbsp;AIMCS&nbsp;AIMCS&nbsp;AIMCS&nbsp;AIMCS&nbsp;AIMCS&nbsp;AIMCS&nbsp;</span>
            </div>
        </div>
        <div class="w-full overflow-hidden whitespace-nowrap text-[11rem] font-bold font-outfit uppercase tracking-[2.5rem] text-transparent" style="-webkit-text-stroke: 2px rgba(245, 158, 11, 0.4);">
            <div class="kinetic-track-right">
                <span>AIMCS&nbsp;AIMCS&nbsp;AIMCS&nbsp;AIMCS&nbsp;AIMCS&nbsp;AIMCS&nbsp;</span>
                <span>AIMCS&nbsp;AIMCS&nbsp;AIMCS&nbsp;AIMCS&nbsp;AIMCS&nbsp;AIMCS&nbsp;</span>
            </div>
        </div>
        <div class="w-full overflow-hidden whitespace-nowrap text-[7rem] font-black font-outfit uppercase tracking-[2rem] text-transparent" style="-webkit-text-stroke: 1.5px rgba(251, 191, 36, 0.3);">
            <div class="kinetic-track-left">
                <span>AIMCS&nbsp;AIMCS&nbsp;AIMCS&nbsp;AIMCS&nbsp;AIMCS&nbsp;AIMCS&nbsp;AIMCS&nbsp;AIMCS&nbsp;</span>
                <span>AIMCS&nbsp;AIMCS&nbsp;AIMCS&nbsp;AIMCS&nbsp;AIMCS&nbsp;AIMCS&nbsp;AIMCS&nbsp;AIMCS&nbsp;</span>
            </div>
        </div>
        <div class="w-full overflow-hidden whitespace-nowrap text-[9.5rem] font-black font-outfit uppercase tracking-[1.5rem] text-amber-500/20">
            <div class="kinetic-track-right">
                <span>AIMCS&nbsp;AIMCS&nbsp;AIMCS&nbsp;AIMCS&nbsp;AIMCS&nbsp;AIMCS&nbsp;</span>
                <span>AIMCS&nbsp;AIMCS&nbsp;AIMCS&nbsp;AIMCS&nbsp;AIMCS&nbsp;AIMCS&nbsp;</span>
            </div>
        </div>
    </div>

    {% if current_user.is_authenticated %}
    <aside class="w-72 bg-[#0b0f19]/80 backdrop-blur-md border-r border-slate-800 flex flex-col fixed h-full z-20">
        <div class="p-6 border-b border-slate-800 flex items-center gap-3">
            <div class="bg-slate-800 p-2.5 rounded-xl text-white shadow-md border border-slate-700">
                <i class="fa-solid fa-graduation-cap text-xl"></i>
            </div>
            <div>
                <h1 class="text-xl font-black text-white tracking-wide font-outfit">AIMCS</h1>
                <p class="text-xs text-slate-400">Attendance Manager</p>
            </div>
        </div>
        
        <nav class="flex-1 p-4 space-y-1 mt-3">
            <a href="/" class="flex items-center gap-3.5 px-4 py-3 rounded-xl text-sm font-medium transition-all text-slate-400 hover:bg-slate-800/60 hover:text-white">
                <i class="fa-solid fa-house text-base w-5 text-slate-500"></i> Home Gateway
            </a>
            <a href="/dashboard" class="flex items-center gap-3.5 px-4 py-3 rounded-xl text-sm font-medium transition-all text-slate-400 hover:bg-slate-800/60 hover:text-white">
                <i class="fa-solid fa-chart-pie text-base w-5 text-slate-500"></i> Dashboard
            </a>
            <a href="/scanner" class="flex items-center gap-3.5 px-4 py-3 rounded-xl text-sm font-medium transition-all text-amber-400 bg-amber-500/10 border border-amber-500/20">
                <i class="fa-solid fa-camera-viewfinder text-base w-5 text-amber-500"></i> Live Scanner Kiosk
            </a>
            <a href="/bulk" class="flex items-center gap-3.5 px-4 py-3 rounded-xl text-sm font-medium transition-all text-slate-400 hover:bg-slate-800/60 hover:text-white">
                <i class="fa-solid fa-qrcode text-base w-5 text-slate-500"></i> Create QR Codes
            </a>
            <a href="/analysis" class="flex items-center gap-3.5 px-4 py-3 rounded-xl text-sm font-medium transition-all text-slate-400 hover:bg-slate-800/60 hover:text-white">
                <i class="fa-solid fa-chart-line text-base w-5 text-slate-500"></i> Analytics
            </a>
            <a href="/profile" class="flex items-center gap-3.5 px-4 py-3 rounded-xl text-sm font-medium transition-all text-slate-400 hover:bg-slate-800/60 hover:text-white">
                <i class="fa-solid fa-key text-base w-5 text-slate-500"></i> Change Password
            </a>
            <a href="/logout" class="flex items-center gap-3.5 px-4 py-3 rounded-xl text-sm font-medium transition-all text-rose-400 hover:bg-rose-500/10 hover:text-rose-300">
                <i class="fa-solid fa-right-from-bracket text-base w-5"></i> Logout
            </a>
        </nav>

        <div class="p-4 border-t border-slate-800">
            <div class="bg-slate-900/60 p-4 rounded-xl border border-slate-800/80 flex items-center gap-3">
                <div class="w-9 h-9 rounded-full bg-slate-800 text-white flex items-center justify-center font-bold text-sm border border-slate-700">
                    {{ current_user.username[0].upper() }}
                </div>
                <div class="truncate">
                    <p class="text-xs font-semibold text-white truncate font-outfit">{{ current_user.username }}</p>
                    <p class="text-[10px] text-amber-400 truncate font-mono">Active Session</p>
                </div>
            </div>
        </div>
    </aside>
    {% endif %}

    <main class="flex-1 {% if current_user.is_authenticated %}pl-72{% endif %} min-h-screen flex flex-col relative z-10">
        <header id="mainHeader" class="h-20 bg-[#030712]/60 backdrop-blur-md border-b border-slate-800 flex items-center justify-between px-8 sticky top-0 z-30">
            <div class="flex items-center gap-2">
                <span class="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
                <p class="text-xs font-semibold tracking-wider text-slate-400 uppercase font-outfit">AIMCS System Online</p>
            </div>
            <div class="text-xs font-medium text-slate-300 bg-slate-900/60 px-4 py-2 rounded-xl border border-slate-800">
                <i class="fa-regular fa-clock mr-2 text-amber-500"></i> <span id="liveClock" class="font-mono"></span>
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
            <h2 class="text-3xl font-bold text-white tracking-tight font-outfit">Live Kiosk Scanner</h2>
            <p class="text-sm text-slate-400 mt-1">Point a student's QR code at the camera. It scans instantly like NFC.</p>
        </div>
        
        <div class="bg-[#0b0f19]/80 backdrop-blur-xl border border-slate-800 rounded-2xl p-6 shadow-[0_0_40px_-15px_rgba(245,158,11,0.15)] relative">
            
            <div class="absolute inset-0 border-2 border-amber-500/20 rounded-2xl m-6 pointer-events-none z-10">
                <div class="absolute top-0 left-0 w-8 h-8 border-t-2 border-l-2 border-amber-500"></div>
                <div class="absolute top-0 right-0 w-8 h-8 border-t-2 border-r-2 border-amber-500"></div>
                <div class="absolute bottom-0 left-0 w-8 h-8 border-b-2 border-l-2 border-amber-500"></div>
                <div class="absolute bottom-0 right-0 w-8 h-8 border-b-2 border-r-2 border-amber-500"></div>
            </div>

            <div id="reader" class="w-full rounded-xl overflow-hidden relative z-0 min-h-[300px] flex items-center justify-center bg-slate-900"></div>
            
            <div id="scanResult" class="hidden mt-4 p-4 rounded-xl text-center font-bold text-sm shadow-md transition-all duration-300"></div>
        </div>

        <script src="https://unpkg.com/html5-qrcode"></script>
        <script>
            let html5QrcodeScanner;
            
            function onScanSuccess(decodedText, decodedResult) {
                // Pause the scanner to prevent double-scanning the same code rapidly
                html5QrcodeScanner.pause();
                
                // Extract token from URL
                let token = '';
                try {
                    token = decodedText.split('/mark/')[1];
                } catch(e) {}

                if (!token) {
                    showResult("Unrecognized QR Code Format", "error");
                    setTimeout(() => html5QrcodeScanner.resume(), 2500);
                    return;
                }

                // Call the background API
                fetch('/api/mark/' + token)
                    .then(res => res.json())
                    .then(data => {
                        showResult(data.message, data.status);
                        // Resume scanning after 2.5 seconds automatically
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
                resDiv.classList.remove('hidden', 'bg-emerald-500/10', 'text-emerald-400', 'bg-rose-500/10', 'text-rose-400', 'bg-amber-500/10', 'text-amber-400', 'border-emerald-500/20', 'border-rose-500/20', 'border-amber-500/20');
                
                if (type === 'success') {
                    resDiv.classList.add('bg-emerald-500/10', 'text-emerald-400', 'border', 'border-emerald-500/20');
                    resDiv.innerHTML = `<i class="fa-solid fa-circle-check text-xl mb-1 block"></i> <span class="font-outfit uppercase tracking-wider">${msg}</span>`;
                } else if (type === 'error') {
                    resDiv.classList.add('bg-rose-500/10', 'text-rose-400', 'border', 'border-rose-500/20');
                    resDiv.innerHTML = `<i class="fa-solid fa-circle-xmark text-xl mb-1 block"></i> <span class="font-outfit uppercase tracking-wider">${msg}</span>`;
                } else {
                    resDiv.classList.add('bg-amber-500/10', 'text-amber-400', 'border', 'border-amber-500/20');
                    resDiv.innerHTML = `<i class="fa-solid fa-triangle-exclamation text-xl mb-1 block"></i> <span class="font-outfit uppercase tracking-wider">${msg}</span>`;
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
    """
    Silent background endpoint used by the Live Scanner to quickly tap-and-go 
    without redirecting the admin away from the camera feed.
    """
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
            error_msg = "Invalid username or password."

    content = f"""
    <div class="relative z-20 max-w-md w-full mx-auto my-auto bg-[#0b0f19]/80 backdrop-blur-xl border border-slate-800/90 rounded-2xl p-8 space-y-6 shadow-[0_0_40px_-15px_rgba(245,158,11,0.15)]">
        <div class="text-center space-y-2">
            <div class="inline-flex p-3.5 bg-slate-900 border border-slate-800 text-amber-500 rounded-xl mb-1 shadow-inner">
                <i class="fa-solid fa-lock text-2xl"></i>
            </div>
            <h2 class="text-2xl font-bold text-white tracking-tight font-outfit">Admin Sign In</h2>
            <p class="text-xs text-slate-400">Enter account details to connect to the AIMCS matrix.</p>
        </div>
        
        {f'<div class="p-3 bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs rounded-xl font-medium text-center">{error_msg}</div>' if error_msg else ''}

        <form method="POST" class="space-y-4">
            <div class="space-y-1">
                <label class="text-[11px] font-bold text-slate-400 uppercase tracking-wide font-outfit">Username</label>
                <input type="text" name="username" class="w-full bg-slate-900/60 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-amber-500/50 transition-colors" placeholder="Enter username" required>
            </div>
            <div class="space-y-1">
                <label class="text-[11px] font-bold text-slate-400 uppercase tracking-wide font-outfit">Password</label>
                <input type="password" name="password" class="w-full bg-slate-900/60 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-amber-500/50 transition-colors" placeholder="Enter password" required>
            </div>
            <button type="submit" class="w-full inline-flex items-center justify-center px-4 py-3 bg-amber-500 hover:bg-amber-600 text-[#030712] font-bold rounded-xl text-sm transition-all border border-amber-400 shadow-md">
                Sign In
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
            status_msg = """<div class="p-3 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs rounded-xl font-medium text-center">Password updated successfully.</div>"""
        else:
            status_msg = """<div class="p-3 bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs rounded-xl font-medium text-center">Current password is incorrect.</div>"""
        conn.close()

    content = f"""
    <div class="max-w-xl mx-auto bg-[#0b0f19]/80 backdrop-blur-md border border-slate-800 rounded-2xl p-8 space-y-6 shadow-xl">
        <div class="border-b border-slate-800 pb-3">
            <h2 class="text-xl font-bold text-white tracking-tight font-outfit">Change Password</h2>
        </div>

        {status_msg}

        <form method="POST" class="space-y-4">
            <div class="space-y-1">
                <label class="text-xs font-bold text-slate-400 uppercase tracking-wide font-outfit">Current Password</label>
                <input type="password" name="old_password" class="w-full bg-slate-900 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-amber-500/50 transition-colors" required>
            </div>
            <div class="space-y-1">
                <label class="text-xs font-bold text-slate-400 uppercase tracking-wide font-outfit">New Password</label>
                <input type="password" name="new_password" class="w-full bg-slate-900 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-amber-500/50 transition-colors" required>
            </div>
            <button type="submit" class="w-full inline-flex items-center justify-center px-4 py-3 bg-amber-500 hover:bg-amber-600 text-[#030712] font-bold rounded-xl text-sm transition-all border border-amber-400 shadow-md">
                Save Changes
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
        <div class="relative w-full rounded-2xl overflow-hidden border border-slate-800/80 bg-[#0b0f19]/80 backdrop-blur-md shadow-[0_0_50px_-15px_rgba(245,158,11,0.1)] p-12 md:p-16">
            <div class="absolute inset-0 pointer-events-none select-none overflow-hidden opacity-30 flex flex-col justify-between py-6 z-0">
                <div class="w-full overflow-hidden whitespace-nowrap">
                    <div class="kinetic-track-left text-[6rem] font-black font-outfit tracking-[2rem] text-transparent" style="-webkit-text-stroke: 1.5px rgba(245, 158, 11, 0.4);">
                        <span>AIMCS&nbsp;AIMCS&nbsp;AIMCS&nbsp;AIMCS&nbsp;AIMCS&nbsp;AIMCS&nbsp;</span>
                        <span>AIMCS&nbsp;AIMCS&nbsp;AIMCS&nbsp;AIMCS&nbsp;AIMCS&nbsp;AIMCS&nbsp;</span>
                    </div>
                </div>
                
                <div class="absolute inset-0 flex items-center justify-center font-outfit font-black text-[14rem] text-transparent bg-clip-text bg-gradient-to-b from-amber-500/20 via-amber-500/5 to-transparent tracking-widest uppercase motion-center-glow z-0">
                    AIMCS
                </div>

                <div class="w-full overflow-hidden whitespace-nowrap">
                    <div class="kinetic-track-right text-[5rem] font-bold font-outfit tracking-[3rem] text-transparent" style="-webkit-text-stroke: 1px rgba(251, 191, 36, 0.3);">
                        <span>AIMCS&nbsp;AIMCS&nbsp;AIMCS&nbsp;AIMCS&nbsp;AIMCS&nbsp;AIMCS&nbsp;</span>
                        <span>AIMCS&nbsp;AIMCS&nbsp;AIMCS&nbsp;AIMCS&nbsp;AIMCS&nbsp;AIMCS&nbsp;</span>
                    </div>
                </div>
            </div>

            <div class="absolute inset-0 bg-gradient-to-r from-[#0b0f19] via-[#0b0f19]/80 to-transparent z-10"></div>

            <div class="relative z-20 max-w-xl space-y-5">
                <div class="space-y-1">
                    <h2 class="text-7xl font-black text-transparent bg-clip-text bg-gradient-to-b from-amber-100 via-amber-400 to-amber-700 tracking-wider font-outfit drop-shadow-lg">
                        AIMCS
                    </h2>
                    <h3 class="text-xs text-amber-500/80 font-bold tracking-[0.3em] font-outfit uppercase">
                        Enterprise Attendance Core
                    </h3>
                </div>
                
                <p class="text-sm text-slate-300 leading-relaxed font-light border-l border-amber-500/50 pl-4">
                    Generate temporary tokenized QR codes, stream real-time logs, verify security stamps, and launch the Live Kiosk Scanner to rapidly scan students like an NFC tap.
                </p>
                
                <div class="pt-2 flex gap-3">
                    <a href="/dashboard" class="inline-flex items-center justify-center px-6 py-3 bg-amber-500 hover:bg-amber-600 text-[#030712] text-xs font-bold rounded-xl transition-all border border-amber-400 shadow-md">
                        Open Dashboard Portal <i class="fa-solid fa-arrow-right ml-2 text-xs"></i>
                    </a>
                    <a href="/scanner" class="inline-flex items-center justify-center px-6 py-3 bg-slate-900 hover:bg-slate-800 text-amber-400 text-xs font-bold rounded-xl transition-all border border-slate-700 shadow-md">
                        <i class="fa-solid fa-camera mr-2 text-xs"></i> Launch Live Scanner
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
            <h2 class="text-2xl font-bold text-white tracking-tight font-outfit">System Overview</h2>
            <p class="text-xs text-slate-400 mt-0.5">Summary indexes and administrative tools pipeline.</p>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-5">
            <div class="bg-[#0b0f19]/80 backdrop-blur-md border border-slate-800 p-6 rounded-2xl flex items-center justify-between shadow-md hover:border-amber-500/30 transition-colors">
                <div class="space-y-0.5">
                    <p class="text-xs font-medium text-slate-400">Registered Students</p>
                    <h3 class="text-3xl font-bold text-white font-outfit tracking-tight">{students}</h3>
                </div>
                <div class="h-10 w-10 bg-slate-900 border border-slate-800 text-amber-500 rounded-xl flex items-center justify-center text-base shadow-sm">
                    <i class="fa-solid fa-users"></i>
                </div>
            </div>

            <div class="bg-[#0b0f19]/80 backdrop-blur-md border border-slate-800 p-6 rounded-2xl flex items-center justify-between shadow-md hover:border-amber-500/30 transition-colors">
                <div class="space-y-0.5">
                    <p class="text-xs font-medium text-slate-400">Total Scan Logs</p>
                    <h3 class="text-3xl font-bold text-white font-outfit tracking-tight">{attendance}</h3>
                </div>
                <div class="h-10 w-10 bg-slate-900 border border-slate-800 text-amber-500 rounded-xl flex items-center justify-center text-base shadow-sm">
                    <i class="fa-solid fa-circle-check"></i>
                </div>
            </div>

            <div class="bg-[#0b0f19]/80 backdrop-blur-md border border-slate-800 p-6 rounded-2xl flex items-center justify-between shadow-md hover:border-emerald-500/30 transition-colors">
                <div class="space-y-0.5">
                    <p class="text-xs font-medium text-slate-400">System Status</p>
                    <h3 class="text-base font-bold text-emerald-400 font-outfit mt-1">Operational</h3>
                </div>
                <div class="h-10 w-10 bg-emerald-500/10 border border-emerald-500/20 text-emerald-500 rounded-xl flex items-center justify-center text-base shadow-sm">
                    <i class="fa-solid fa-server"></i>
                </div>
            </div>
        </div>

        <div class="bg-[#0b0f19]/80 backdrop-blur-md border border-slate-800 rounded-2xl p-6 shadow-md">
            <h3 class="text-sm font-semibold text-white mb-4 uppercase tracking-wider font-outfit">Management Actions</h3>
            <div class="grid grid-cols-1 sm:grid-cols-4 gap-4">
                <a href="/scanner" class="flex flex-col items-center justify-center p-5 bg-amber-500/10 hover:bg-amber-500/20 hover:border-amber-400 rounded-xl border border-amber-500/40 text-center group transition-all">
                    <i class="fa-solid fa-camera-viewfinder text-xl text-amber-500 mb-2 group-hover:scale-105 transition-all"></i>
                    <span class="text-xs font-semibold text-white transition-colors">Open Scanner Kiosk</span>
                </a>
                <a href="/bulk" class="flex flex-col items-center justify-center p-5 bg-slate-900/50 hover:bg-amber-500/10 hover:border-amber-500/40 rounded-xl border border-slate-800 text-center group transition-all">
                    <i class="fa-solid fa-qrcode text-xl text-slate-400 mb-2 group-hover:text-amber-500 group-hover:scale-105 transition-all"></i>
                    <span class="text-xs font-semibold text-white group-hover:text-amber-400 transition-colors">Create QR Codes</span>
                </a>
                <a href="/download" class="flex flex-col items-center justify-center p-5 bg-slate-900/50 hover:bg-amber-500/10 hover:border-amber-500/40 rounded-xl border border-slate-800 text-center group transition-all">
                    <i class="fa-solid fa-file-excel text-xl text-slate-400 mb-2 group-hover:text-amber-500 group-hover:scale-105 transition-all"></i>
                    <span class="text-xs font-semibold text-white group-hover:text-amber-400 transition-colors">Export Excel Sheet</span>
                </a>
                <a href="/download_qrs" class="flex flex-col items-center justify-center p-5 bg-slate-900/50 hover:bg-amber-500/10 hover:border-amber-500/40 rounded-xl border border-slate-800 text-center group transition-all">
                    <i class="fa-solid fa-file-zipper text-xl text-slate-400 mb-2 group-hover:text-amber-500 group-hover:scale-105 transition-all"></i>
                    <span class="text-xs font-semibold text-white group-hover:text-amber-400 transition-colors">Download All QRs</span>
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
        <div class="max-w-xl mx-auto bg-[#0b0f19]/80 backdrop-blur-md border border-slate-800 rounded-2xl p-8 text-center space-y-5 shadow-[0_0_40px_-15px_rgba(245,158,11,0.15)]">
            <div class="inline-flex p-3.5 bg-emerald-500/10 text-emerald-400 rounded-full border border-emerald-500/20">
                <i class="fa-solid fa-circle-check text-3xl"></i>
            </div>
            <h2 class="text-2xl font-bold text-white tracking-tight font-outfit">QR Batch Generated</h2>
            <p class="text-slate-400 text-sm max-w-sm mx-auto leading-relaxed">
                Successfully configured tokens for <span class="text-amber-500 font-bold">{success}</span> student(s). Automated relays are firing notifications via EmailJS.
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

            <div class="pt-4 border-t border-slate-800">
                <a href='/dashboard' class="inline-flex items-center justify-center px-5 py-2 bg-amber-500 hover:bg-amber-600 text-[#030712] text-xs font-bold rounded-xl border border-amber-400 shadow-md">
                    Return to Dashboard
                </a>
            </div>
        </div>
        """
        return render_template_string(LAYOUT_TEMPLATE, content=content)

    content = """
    <div class="max-w-2xl mx-auto bg-[#0b0f19]/80 backdrop-blur-md border border-slate-800 rounded-2xl p-8 space-y-6 shadow-md">
        <div class="border-b border-slate-800 pb-3">
            <h2 class="text-xl font-bold text-white tracking-tight font-outfit">Generate QR Codes in Bulk</h2>
            <p class="text-xs text-slate-400 mt-1">Configure expiration horizons and paste the directory entries.</p>
        </div>

        <form method='POST' class="space-y-5">
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div class="space-y-1">
                    <label class='text-[11px] font-bold text-slate-400 uppercase tracking-wide font-outfit'>Validity Lock Starts</label>
                    <input type='datetime-local' name='start_time' class='w-full bg-slate-900/60 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-amber-500/50 transition-colors' required>
                </div>
                <div class="space-y-1">
                    <label class='text-[11px] font-bold text-slate-400 uppercase tracking-wide font-outfit'>Validity Lock Closes</label>
                    <input type='datetime-local' name='end_time' class='w-full bg-slate-900/60 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-amber-500/50 transition-colors' required>
                </div>
            </div>

            <div class="space-y-1">
                <label class='text-[11px] font-bold text-slate-400 uppercase tracking-wide font-outfit'>Recipient Profiles Matrix (Format: Name, Email)</label>
                <textarea name='data' class='w-full h-40 bg-slate-900/60 border border-slate-800 rounded-xl p-4 text-xs text-white focus:outline-none focus:border-amber-500/50 transition-colors font-mono' placeholder="John Doe, john@example.com&#10;Jane Smith, jane@example.com" required></textarea>
                <p class="text-[11px] text-slate-500 italic mt-1">One record line configuration per student separated by commas.</p>
            </div>
            
            <button type='submit' class="w-full inline-flex items-center justify-center px-4 py-3 bg-amber-500 hover:bg-amber-600 text-[#030712] font-bold rounded-xl text-sm border border-amber-400 shadow-md transition-all">
                Deploy & Broadcast QR Codes
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
            plt.gcf().patch.set_facecolor('#0b0f19')
            plt.gcf().patch.set_alpha(0.0)
            ax = plt.gca()
            ax.set_facecolor('#0b0f19')
            ax.patch.set_alpha(0.0)
            
            attendance_counts.plot(kind='bar', color='#f59e0b', width=0.35, ax=ax)
            
            ax.tick_params(colors='#94a3b8', labelsize=8)
            ax.spines['bottom'].set_color('#334155')
            ax.spines['left'].set_color('#334155')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.grid(axis='y', color='#334155', linestyle='--', alpha=0.2)
            
            plt.title("Attendance Metrics Graph", color='white', fontsize=11, pad=10, weight='bold')
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
            <tr class="border-b border-slate-800/60 text-slate-300 text-xs hover:bg-slate-800/40 transition-colors">
                <td class="px-5 py-3 font-mono text-slate-500">#{row['id']}</td>
                <td class="px-5 py-3 font-semibold text-white">{row['name']}</td>
                <td class="px-5 py-3 font-mono text-slate-400">{row['time']}</td>
                <td class="px-5 py-3"><span class="px-2 py-0.5 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-full text-[10px] font-bold">VERIFIED</span></td>
            </tr>
            """
    else:
        table_rows = """
        <tr>
            <td colspan="4" class="px-5 py-10 text-center text-xs text-slate-500">No telemetry logs available in database storage.</td>
        </tr>
        """

    content = f"""
    <div class="space-y-6 w-full max-w-4xl mx-auto">
        <div>
            <h2 class="text-2xl font-bold text-white tracking-tight font-outfit">Attendance Analytics</h2>
            <p class="text-xs text-slate-400 mt-0.5">Track system deployment logs, active student registers, and validation checkpoints.</p>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-3 gap-5">
            <div class="lg:col-span-1 bg-[#0b0f19]/80 backdrop-blur-md border border-slate-800 rounded-2xl p-4 flex flex-col justify-center items-center shadow-md">
                {f'<img src="{chart_url}" class="w-full" />' if chart_url else '<div class="text-slate-500 text-xs text-center py-12">Insufficient metric indexes to formulate graph vector.</div>'}
            </div>
            
            <div class="lg:col-span-2 bg-[#0b0f19]/80 backdrop-blur-md border border-slate-800 rounded-2xl p-5 space-y-3 shadow-md">
                <h3 class="text-xs font-bold text-white uppercase tracking-wider font-outfit">Active Registration Directories</h3>
                <div class="overflow-x-auto border border-slate-800 rounded-xl bg-slate-900/40">
                    <table class="w-full text-left border-collapse">
                        <thead>
                            <tr class="bg-slate-900 border-b border-slate-800 text-[10px] font-bold text-amber-500 uppercase tracking-wider">
                                <th class="px-5 py-2.5">Index</th>
                                <th class="px-5 py-2.5">Identifier</th>
                                <th class="px-5 py-2.5">Scan Window Authorization Horizon</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-slate-800/40 text-xs text-slate-300">
                            {"".join([f'<tr class="hover:bg-slate-800/40 transition-colors"><td class="px-5 py-2.5 font-mono text-slate-500">#{i+1}</td><td class="px-5 py-2.5 font-semibold text-white">{r["name"]}</td><td class="px-5 py-2.5 font-mono text-slate-400 text-[11px]">{r["start_time"]} to {r["end_time"]}</td></tr>' for i, r in df_config.iterrows()]) if not df_config.empty else '<tr><td colspan="3" class="px-5 py-5 text-center text-slate-500">No profile parameters defined.</td></tr>'}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <div class="bg-[#0b0f19]/80 backdrop-blur-md border border-slate-800 rounded-2xl p-5 shadow-md">
            <h3 class="text-xs font-bold text-white uppercase tracking-wider mb-3 font-outfit">Live Synchronization Stream</h3>
            <div class="overflow-hidden border border-slate-800 rounded-xl bg-slate-900/40">
                <div class="max-h-64 overflow-y-auto">
                    <table class="w-full text-left border-collapse">
                        <thead class="sticky top-0 bg-slate-900 border-b border-slate-800 text-[10px] font-bold text-amber-500 uppercase tracking-wider z-10">
                            <tr>
                                <th class="px-5 py-2.5">Log ID</th>
                                <th class="px-5 py-2.5">Client Token Name</th>
                                <th class="px-5 py-2.5">Timestamp</th>
                                <th class="px-5 py-2.5">Authentication</th>
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
    font-family: 'Inter', system-ui, sans-serif; 
    text-align: center; 
    padding: 80px 16px; 
    background-color: #030712; 
    color: #f8fafc; 
    min-height: 100vh; 
    box-sizing: border-box; 
    display: flex; 
    align-items: center; 
    justify-content: center;
    """
    
    PANEL_CARD_STYLE = """
    max-width: 460px; 
    width: 100%; 
    background-color: #0b0f19; 
    border: 1px solid #1e293b; 
    padding: 40px 24px; 
    border-radius: 20px; 
    box-shadow: 0 20px 40px -15px rgba(245,158,11,0.1);
    """

    if not data:
        conn.close()
        return f"""
        <div style="{PAGE_BODY_STYLE}">
            <div style="{PANEL_CARD_STYLE}">
                <div style="color:#ef4444; font-size:44px; margin-bottom:14px;">✖</div>
                <h2 style="margin:0 0 6px 0; font-size:20px; font-weight:700;">Invalid Link Identifier</h2>
                <p style="color:#94a3b8; font-size:13px; line-height:1.5; margin:0;">This attendance verification matrix is missing or expired.</p>
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
                <div style="color:#f59e0b; font-size:44px; margin-bottom:14px;">🛑</div>
                <h2 style="margin:0 0 6px 0; font-size:20px; font-weight:700;">Transmission Sealed</h2>
                <p style="color:#94a3b8; font-size:13px; margin:0 0 16px 0; line-height:1.5;">This attendance scan gateway has not activated yet.</p>
                <div style="background-color:#1e293b; padding:12px; border-radius:10px; font-family:monospace; font-size:12px; color:#94a3b8;">
                    Scheduled Release: <br/><strong style="font-size:14px; color:#f59e0b; display:block; margin-top:4px;">{start_dt.strftime('%Y-%m-%d %H:%M')}</strong>
                </div>
            </div>
        </div>
        """

    if now > end_dt:
        conn.close()
        return f"""
        <div style="{PAGE_BODY_STYLE}">
            <div style="{PANEL_CARD_STYLE}">
                <div style="color:#ef4444; font-size:44px; margin-bottom:14px;">⚠️</div>
                <h2 style="margin:0 0 6px 0; font-size:20px; font-weight:700;">Gateway Terminated</h2>
                <p style="color:#94a3b8; font-size:13px; margin:0 0 16px 0; line-height:1.5;">The verification timeout configuration limit has passed.</p>
                <div style="background-color:#1e293b; padding:12px; border-radius:10px; font-family:monospace; font-size:12px; color:#f43f5e;">
                    Terminated At: <br/><strong style="font-size:14px; color:#fff; display:block; margin-top:4px;">{end_dt.strftime('%Y-%m-%d %H:%M')}</strong>
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
                <div style="color:#3b82f6; font-size:44px; margin-bottom:14px;">🔁</div>
                <h2 style="margin:0 0 6px 0; font-size:20px; font-weight:700;">Telemetry Authenticated</h2>
                <p style="color:#94a3b8; font-size:13px; margin:0 0 14px 0; line-height:1.5;">Your daily log allocation has already been safely committed.</p>
                <div style="border-top:1px solid #1e293b; padding-top:14px;">
                    <h3 style="color:#ffffff; margin:0; font-size:17px; font-weight:600;">{name}</h3>
                    <p style="color:#3b82f6; font-size:11px; text-transform:uppercase; font-weight:bold; margin-top:3px; letter-spacing:0.5px;">Status: Validated</p>
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
            <div style="color:#10b981; font-size:44px; margin-bottom:14px;">✅</div>
            <h2 style="margin:0 0 6px 0; font-size:20px; font-weight:700; color:#10b981;">Log Comitted Successfully</h2>
            <p style="color:#94a3b8; font-size:13px; margin:0 0 16px 0; line-height:1.5;">Attendance has been successfully written to the mainframe database logs.</p>
            <div style="background:rgba(16,185,129,0.05); border:1px solid rgba(16,185,129,0.15); padding:14px; border-radius:10px;">
                <h3 style="color:#ffffff; margin:0; font-size:17px; font-weight:600;">{name}</h3>
                <p style="color:#10b981; font-size:11px; font-family:monospace; margin-top:3px; font-weight:bold;">{time_str}</p>
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
