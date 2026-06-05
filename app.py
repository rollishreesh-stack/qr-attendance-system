from flask import Flask, request, redirect, send_file, render_template_string, url_for, flash
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
matplotlib.use('Agg')  # Prevents GUI compilation issues on hosting platforms
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

    # Setup default admin account if table is empty (User: admin / Pass: admin123)
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

# ================= PREMIUM MASTER LAYOUT =================
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

        /* Seamless Infinite Kinetic Typography Keyframes */
        @keyframes marqueeLeft {
            0% { transform: translate3d(0, 0, 0); }
            100% { transform: translate3d(-50%, 0, 0); }
        }
        @keyframes marqueeRight {
            0% { transform: translate3d(-50%, 0, 0); }
            100% { transform: translate3d(0, 0, 0); }
        }
        @keyframes subtlePulse {
            0%, 100% { opacity: 0.02; transform: scale(0.98); }
            50% { opacity: 0.08; transform: scale(1.02); }
        }

        .motion-canvas-left {
            display: inline-block;
            white-space: nowrap;
            animation: marqueeLeft 28s linear infinite;
        }
        .motion-canvas-right {
            display: inline-block;
            white-space: nowrap;
            animation: marqueeRight 32s linear infinite;
        }
        .motion-center-glow {
            animation: subtlePulse 4s ease-in-out infinite;
        }
        
        /* Smooth Scrollbars for premium finish */
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
        ::-webkit-scrollbar-thumb:hover {
            background: #334155;
        }
    </style>
</head>
<body class="text-slate-300 min-h-screen flex">

    {% if current_user.is_authenticated %}
    <!-- Sidebar Menu Navigation -->
    <aside class="w-72 bg-[#0b0f19] border-r border-slate-800 flex flex-col fixed h-full z-20">
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
            <div class="bg-slate-900/50 p-4 rounded-xl border border-slate-800/80 flex items-center gap-3">
                <div class="w-9 h-9 rounded-full bg-slate-800 text-white flex items-center justify-center font-bold text-sm border border-slate-700">
                    {{ current_user.username[0].upper() }}
                </div>
                <div class="truncate">
                    <p class="text-xs font-semibold text-white truncate font-outfit">{{ current_user.username }}</p>
                    <p class="text-[10px] text-emerald-400 truncate font-mono">Active Session</p>
                </div>
            </div>
        </div>
    </aside>
    {% endif %}

    <!-- Core Content Container -->
    <main class="flex-1 {% if current_user.is_authenticated %}pl-72{% endif %} min-h-screen flex flex-col relative overflow-hidden">
        <header class="h-20 bg-[#030712]/40 backdrop-blur-md border-b border-slate-800 flex items-center justify-between px-8 id="mainHeader" class="sticky top-0 z-30">
            <div class="flex items-center gap-2">
                <span class="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
                <p class="text-xs font-semibold tracking-wider text-slate-400 uppercase font-outfit">AIMCS System Online</p>
            </div>
            <div class="text-xs font-medium text-slate-300 bg-slate-900/50 px-4 py-2 rounded-xl border border-slate-800">
                <i class="fa-regular fa-clock mr-2 text-slate-400"></i> <span id="liveClock" class="font-mono"></span>
            </div>
        </header>

        <div class="p-8 flex-1 flex flex-col justify-start max-w-6xl w-full mx-auto relative z-10">
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

# ================= LOGIN ROUTE (FULL SCREEN KINETIC CANVAS) =================
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
    <!-- Full Screen Fixed Kinetic Wallpapers -->
    <div class="fixed inset-0 pointer-events-none select-none overflow-hidden w-screen h-screen z-0 bg-[#030712] flex flex-col justify-between py-10">
        
        <!-- Track Row 1 -->
        <div class="w-full overflow-hidden whitespace-nowrap opacity-[0.04]">
            <div class="motion-canvas-left text-[9rem] font-black font-outfit uppercase tracking-[2rem] text-white">
                AIMCS AIMCS AIMCS AIMCS AIMCS AIMCS AIMCS AIMCS AIMCS AIMCS AIMCS AIMCS AIMCS AIMCS AIMCS AIMCS
            </div>
        </div>
        
        <!-- Track Row 2 -->
        <div class="w-full overflow-hidden whitespace-nowrap opacity-[0.06]">
            <div class="motion-canvas-right text-[11rem] font-bold font-outfit uppercase tracking-[3rem] text-transparent" style="-webkit-text-stroke: 2px white;">
                AIMCS AIMCS AIMCS AIMCS AIMCS AIMCS AIMCS AIMCS AIMCS AIMCS AIMCS AIMCS AIMCS AIMCS AIMCS AIMCS
            </div>
        </div>

        <!-- Track Row 3 -->
        <div class="w-full overflow-hidden whitespace-nowrap opacity-[0.03]">
            <div class="motion-canvas-left text-[8rem] font-black font-outfit uppercase tracking-[1.5rem] text-transparent" style="-webkit-text-stroke: 1.5px white;">
                AIMCS AIMCS AIMCS AIMCS AIMCS AIMCS AIMCS AIMCS AIMCS AIMCS AIMCS AIMCS AIMCS AIMCS AIMCS AIMCS
            </div>
        </div>

        <!-- Track Row 4 -->
        <div class="w-full overflow-hidden whitespace-nowrap opacity-[0.05]">
            <div class="motion-canvas-right text-[10rem] font-black font-outfit uppercase tracking-[2.5rem] text-white">
                AIMCS AIMCS AIMCS AIMCS AIMCS AIMCS AIMCS AIMCS AIMCS AIMCS AIMCS AIMCS AIMCS AIMCS AIMCS AIMCS
            </div>
        </div>

        <!-- Huge Layered Static Focal Backdrop Lettering -->
        <div class="absolute inset-0 flex items-center justify-center z-10 pointer-events-none">
            <div class="font-outfit font-black text-[22rem] md:text-[28rem] text-transparent bg-clip-text bg-gradient-to-b from-white/10 via-white/[0.01] to-transparent tracking-widest uppercase motion-center-glow">
                AIMCS
            </div>
        </div>

        <!-- Ambient Blending Overlays -->
        <div class="absolute inset-0 bg-gradient-to-t from-[#030712] via-transparent to-[#030712] z-11"></div>
        <div class="absolute inset-0 bg-gradient-to-r from-[#030712] via-transparent to-[#030712] z-11"></div>
    </div>

    <!-- Floating Frosted Login Card -->
    <div class="relative z-20 max-w-md w-full mx-auto my-auto bg-[#0b0f19]/80 backdrop-blur-xl border border-slate-800/90 rounded-2xl p-8 space-y-6 shadow-2xl transition-all">
        <div class="text-center space-y-2">
            <div class="inline-flex p-3.5 bg-slate-900 border border-slate-800 text-slate-300 rounded-xl mb-1">
                <i class="fa-solid fa-lock text-2xl"></i>
            </div>
            <h2 class="text-2xl font-bold text-white tracking-tight font-outfit">Admin Sign In</h2>
            <p class="text-xs text-slate-400">Please enter your account details to access AIMCS.</p>
        </div>
        
        {f'<div class="p-3 bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs rounded-xl font-medium text-center">{error_msg}</div>' if error_msg else ''}

        <form method="POST" class="space-y-4">
            <div class="space-y-1">
                <label class="text-[11px] font-bold text-slate-400 uppercase tracking-wide font-outfit">Username</label>
                <input type="text" name="username" class="w-full bg-slate-900/60 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-slate-600 transition-colors" placeholder="Enter username" required>
            </div>
            <div class="space-y-1">
                <label class="text-[11px] font-bold text-slate-400 uppercase tracking-wide font-outfit">Password</label>
                <input type="password" name="password" class="w-full bg-slate-900/60 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-slate-600 transition-colors" placeholder="Enter password" required>
            </div>
            <button type="submit" class="w-full inline-flex items-center justify-center px-4 py-3 bg-slate-800 hover:bg-slate-700 text-white font-bold rounded-xl text-sm transition-all border border-slate-700 shadow-md">
                Sign In
            </button>
        </form>
        <div class="text-center text-[11px] text-slate-500 font-mono pt-2 border-t border-slate-900">
            Default Admin account: admin / admin123
        </div>
    </div>
    """
    return render_template_string(LAYOUT_TEMPLATE, content=content)

# ================= FIXED LOGOUT ROUTE =================
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
    <div class="max-w-xl mx-auto bg-[#0b0f19] border border-slate-800 rounded-2xl p-8 space-y-6">
        <div class="border-b border-slate-800 pb-3">
            <h2 class="text-xl font-bold text-white tracking-tight font-outfit">Change Password</h2>
            <p class="text-xs text-slate-400 mt-1">Update your login security credentials here.</p>
        </div>

        {status_msg}

        <form method="POST" class="space-y-4">
            <div class="space-y-1">
                <label class="text-xs font-bold text-slate-400 uppercase tracking-wide font-outfit">Current Password</label>
                <input type="password" name="old_password" class="w-full bg-slate-900 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-slate-600 transition-colors" required>
            </div>
            <div class="space-y-1">
                <label class="text-xs font-bold text-slate-400 uppercase tracking-wide font-outfit">New Password</label>
                <input type="password" name="new_password" class="w-full bg-slate-900 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-slate-600 transition-colors" required>
            </div>
            <button type="submit" class="w-full inline-flex items-center justify-center px-4 py-3 bg-slate-800 hover:bg-slate-700 text-white font-bold rounded-xl text-sm transition-all border border-slate-700 shadow-md">
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
    <div class="w-full max-w-4xl mx-auto mt-6">
        
        <!-- Premium Home Panel with AIMCS Letter Motion Canvas -->
        <div class="relative w-full h-[460px] rounded-2xl overflow-hidden border border-slate-800 bg-[#070b12] shadow-2xl flex items-center px-12 md:px-16">
            
            <!-- AIMCS Letters Motion Background Canvas -->
            <div class="absolute inset-0 pointer-events-none select-none overflow-hidden opacity-30 flex flex-col justify-between py-6">
                <!-- Track 1 -->
                <div class="w-full overflow-hidden whitespace-nowrap">
                    <div class="motion-canvas-left text-[6rem] font-black font-outfit tracking-[2rem] text-transparent" style="-webkit-text-stroke: 1.5px rgba(255,255,255,0.06);">
                        AIMCS AIMCS AIMCS AIMCS AIMCS AIMCS AIMCS AIMCS AIMCS AIMCS AIMCS AIMCS
                    </div>
                </div>
                
                <!-- Center Static Array -->
                <div class="absolute inset-0 flex items-center justify-center font-outfit font-black text-[14rem] text-transparent bg-clip-text bg-gradient-to-b from-white/10 via-white/[0.02] to-transparent tracking-widest uppercase motion-center-glow z-0">
                    AIMCS
                </div>

                <!-- Track 2 -->
                <div class="w-full overflow-hidden whitespace-nowrap">
                    <div class="motion-canvas-right text-[5rem] font-bold font-outfit tracking-[3rem] text-transparent" style="-webkit-text-stroke: 1px rgba(255,255,255,0.04);">
                        AIMCS AIMCS AIMCS AIMCS AIMCS AIMCS AIMCS AIMCS AIMCS AIMCS AIMCS AIMCS
                    </div>
                </div>
            </div>

            <!-- Deep Ambient Gradient Layer over content backdrops -->
            <div class="absolute inset-0 bg-gradient-to-r from-[#030712] via-[#030712]/80 to-transparent z-10"></div>

            <!-- Dashboard Content Layout Panel -->
            <div class="relative z-20 max-w-xl space-y-5">
                <div class="space-y-1">
                    <h2 class="text-6xl md:text-7xl font-black text-transparent bg-clip-text bg-gradient-to-b from-slate-50 via-slate-300 to-slate-500 tracking-wider font-outfit drop-shadow-md">
                        AIMCS
                    </h2>
                    <h3 class="text-lg md:text-xl text-slate-400 font-light tracking-[0.25em] font-outfit uppercase">
                        Attendance Platform
                    </h3>
                </div>
                
                <p class="text-sm text-slate-400 leading-relaxed font-light border-l border-slate-700 pl-4">
                    Create instant student QR codes, manage records, view charts, and download complete reports through a simple administrative control layout.
                </p>
                
                <div class="pt-2">
                    <a href="/dashboard" class="inline-flex items-center justify-center px-6 py-3 bg-slate-800 hover:bg-slate-700 text-white text-xs font-bold rounded-xl transition-all border border-slate-700 shadow-md hover:-translate-y-0.5">
                        Open Dashboard <i class="fa-solid fa-arrow-right ml-2 text-xs"></i>
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
            <p class="text-xs text-slate-400 mt-0.5">Quick summary of logs and database management shortcuts.</p>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-5">
            <div class="bg-[#0b0f19] border border-slate-800 p-6 rounded-2xl flex items-center justify-between shadow-md">
                <div class="space-y-0.5">
                    <p class="text-xs font-medium text-slate-400">Registered Students</p>
                    <h3 class="text-3xl font-bold text-white font-outfit tracking-tight">{students}</h3>
                </div>
                <div class="h-10 w-10 bg-slate-900 border border-slate-800 text-slate-400 rounded-xl flex items-center justify-center text-base shadow-sm">
                    <i class="fa-solid fa-users"></i>
                </div>
            </div>

            <div class="bg-[#0b0f19] border border-slate-800 p-6 rounded-2xl flex items-center justify-between shadow-md">
                <div class="space-y-0.5">
                    <p class="text-xs font-medium text-slate-400">Total Attendance Records</p>
                    <h3 class="text-3xl font-bold text-white font-outfit tracking-tight">{attendance}</h3>
                </div>
                <div class="h-10 w-10 bg-slate-900 border border-slate-800 text-slate-400 rounded-xl flex items-center justify-center text-base shadow-sm">
                    <i class="fa-solid fa-circle-check"></i>
                </div>
            </div>

            <div class="bg-[#0b0f19] border border-slate-800 p-6 rounded-2xl flex items-center justify-between shadow-md">
                <div class="space-y-0.5">
                    <p class="text-xs font-medium text-slate-400">System Status</p>
                    <h3 class="text-base font-bold text-emerald-400 font-outfit mt-1">Operational</h3>
                </div>
                <div class="h-10 w-10 bg-slate-900 border border-slate-800 text-emerald-500 rounded-xl flex items-center justify-center text-base shadow-sm">
                    <i class="fa-solid fa-server"></i>
                </div>
            </div>
        </div>

        <div class="bg-[#0b0f19] border border-slate-800 rounded-2xl p-6 shadow-md">
            <h3 class="text-sm font-semibold text-white mb-4 uppercase tracking-wider font-outfit">Management Options</h3>
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <a href="/bulk" class="flex flex-col items-center justify-center p-5 bg-slate-900/40 hover:bg-slate-800/40 rounded-xl border border-slate-800/80 text-center group transition-all">
                    <i class="fa-solid fa-qrcode text-xl text-slate-400 mb-2 group-hover:scale-105 transition-transform"></i>
                    <span class="text-xs font-semibold text-white">Create QR Codes</span>
                </a>
                <a href="/download" class="flex flex-col items-center justify-center p-5 bg-slate-900/40 hover:bg-slate-800/40 rounded-xl border border-slate-800/80 text-center group transition-all">
                    <i class="fa-solid fa-file-excel text-xl text-slate-400 mb-2 group-hover:scale-105 transition-transform"></i>
                    <span class="text-xs font-semibold text-white">Export Excel Sheet</span>
                </a>
                <a href="/download_qrs" class="flex flex-col items-center justify-center p-5 bg-slate-900/40 hover:bg-slate-800/40 rounded-xl border border-slate-800/80 text-center group transition-all">
                    <i class="fa-solid fa-file-zipper text-xl text-slate-400 mb-2 group-hover:scale-105 transition-transform"></i>
                    <span class="text-xs font-semibold text-white">Download All QRs (.zip)</span>
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
        <div class="max-w-xl mx-auto bg-[#0b0f19] border border-slate-800 rounded-2xl p-8 text-center space-y-5 shadow-2xl">
            <div class="inline-flex p-3.5 bg-emerald-500/10 text-emerald-400 rounded-full border border-emerald-500/20">
                <i class="fa-solid fa-circle-check text-3xl"></i>
            </div>
            <h2 class="text-2xl font-bold text-white tracking-tight font-outfit">QR Codes Created Successfully!</h2>
            <p class="text-slate-400 text-sm max-w-sm mx-auto leading-relaxed">
                Successfully processed profiles for <span class="text-white font-bold">{success}</span> student(s). The platform is now emailing the codes automatically in the background.
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
                );
            }});
            </script>

            <div class="pt-4 border-t border-slate-800">
                <a href='/dashboard' class="inline-flex items-center justify-center px-5 py-2 bg-slate-800 hover:bg-slate-700 text-white text-xs font-semibold rounded-xl border border-slate-700 shadow-md">
                    Go to Dashboard
                </a>
            </div>
        </div>
        """
        return render_template_string(LAYOUT_TEMPLATE, content=content)

    content = """
    <div class="max-w-2xl mx-auto bg-[#0b0f19] border border-slate-800 rounded-2xl p-8 space-y-6 shadow-md">
        <div class="border-b border-slate-800 pb-3">
            <h2 class="text-xl font-bold text-white tracking-tight font-outfit">Generate QR Codes in Bulk</h2>
            <p class="text-xs text-slate-400 mt-1">Set the valid scanning active time frame and paste your list of recipients.</p>
        </div>

        <form method='POST' class="space-y-5">
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div class="space-y-1">
                    <label class='text-[11px] font-bold text-slate-400 uppercase tracking-wide font-outfit'>Start Date & Time</label>
                    <input type='datetime-local' name='start_time' class='w-full bg-slate-900/60 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-slate-600 transition-colors' required>
                </div>
                <div class="space-y-1">
                    <label class='text-[11px] font-bold text-slate-400 uppercase tracking-wide font-outfit'>End Date & Time</label>
                    <input type='datetime-local' name='end_time' class='w-full bg-slate-900/60 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-slate-600 transition-colors' required>
                </div>
            </div>

            <div class="space-y-1">
                <label class='text-[11px] font-bold text-slate-400 uppercase tracking-wide font-outfit'>Student List (Format: Name, Email)</label>
                <textarea name='data' class='w-full h-40 bg-slate-900/60 border border-slate-800 rounded-xl p-4 text-xs text-white focus:outline-none focus:border-slate-600 transition-colors font-mono' placeholder="John Doe, john@example.com&#10;Jane Smith, jane@example.com" required></textarea>
                <p class="text-[11px] text-slate-500 italic mt-1">Enter each student on a separate line with a comma between the name and email.</p>
            </div>
            
            <button type='submit' class="w-full inline-flex items-center justify-center px-4 py-3 bg-slate-800 hover:bg-slate-700 text-white font-bold rounded-xl text-sm border border-slate-700 shadow-md">
                Generate & Email QR Codes
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
            
            attendance_counts.plot(kind='bar', color='#475569', width=0.35, ax=ax)
            
            ax.tick_params(colors='#94a3b8', labelsize=8)
            ax.spines['bottom'].set_color('#334155')
            ax.spines['left'].set_color('#334155')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.grid(axis='y', color='#334155', linestyle='--', alpha=0.2)
            
            plt.title("Attendance Frequency Chart", color='white', fontsize=11, pad=10, weight='bold')
            plt.tight_layout()
            
            img_buf = io.BytesIO()
            plt.savefig(img_buf, format='png', transparent=True, bbox_inches='tight')
            img_buf.seek(0)
            import base64
            chart_url = "data:image/png;base64," + base64.b64encode(img_buf.getvalue()).decode('utf-8')
            plt.close()
        except Exception as e:
            print("Chart building fault logged:", e)

    table_rows = ""
    if not df_logs.empty:
        for idx, row in df_logs.iterrows():
            table_rows += f"""
            <tr class="border-b border-slate-800/60 text-slate-300 text-xs hover:bg-slate-800/20">
                <td class="px-5 py-3 font-mono text-slate-500">#{row['id']}</td>
                <td class="px-5 py-3 font-semibold text-white">{row['name']}</td>
                <td class="px-5 py-3 font-mono text-slate-400">{row['time']}</td>
                <td class="px-5 py-3"><span class="px-2 py-0.5 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-full text-[10px] font-bold">VERIFIED</span></td>
            </tr>
            """
    else:
        table_rows = """
        <tr>
            <td colspan="4" class="px-5 py-10 text-center text-xs text-slate-500">No attendance logs available in the database yet.</td>
        </tr>
        """

    content = f"""
    <div class="space-y-6 w-full max-w-4xl mx-auto">
        <div>
            <h2 class="text-2xl font-bold text-white tracking-tight font-outfit">Attendance Analytics</h2>
            <p class="text-xs text-slate-400 mt-0.5">Track system history charts, registered student lists, and scanning logs.</p>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-3 gap-5">
            <div class="lg:col-span-1 bg-[#0b0f19] border border-slate-800 rounded-2xl p-4 flex flex-col justify-center items-center shadow-md">
                {f'<img src="{chart_url}" class="w-full" />' if chart_url else '<div class="text-slate-500 text-xs text-center py-12">Not enough data to create a graph view yet.</div>'}
            </div>
            
            <div class="lg:col-span-2 bg-[#0b0f19] border border-slate-800 rounded-2xl p-5 space-y-3 shadow-md">
                <h3 class="text-xs font-bold text-white uppercase tracking-wider font-outfit">Registered Student Profiles</h3>
                <div class="overflow-x-auto border border-slate-800 rounded-xl bg-slate-900/20">
                    <table class="w-full text-left border-collapse">
                        <thead>
                            <tr class="bg-slate-900 border-b border-slate-800 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                                <th class="px-5 py-2.5">ID</th>
                                <th class="px-5 py-2.5">Student Name</th>
                                <th class="px-5 py-2.5">Active Validity Hours</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-slate-800/40 text-xs text-slate-300">
                            {"".join([f'<tr><td class="px-5 py-2.5 font-mono text-slate-500">#{i+1}</td><td class="px-5 py-2.5 font-semibold text-white">{r["name"]}</td><td class="px-5 py-2.5 font-mono text-slate-400 text-[11px]">{r["start_time"]} to {r["end_time"]}</td></tr>' for i, r in df_config.iterrows()]) if not df_config.empty else '<tr><td colspan="3" class="px-5 py-5 text-center text-slate-500">No students registered yet.</td></tr>'}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <div class="bg-[#0b0f19] border border-slate-800 rounded-2xl p-5 shadow-md">
            <h3 class="text-xs font-bold text-white uppercase tracking-wider mb-3 font-outfit">Live Attendance Logs</h3>
            <div class="overflow-hidden border border-slate-800 rounded-xl bg-slate-900/20">
                <div class="max-h-64 overflow-y-auto">
                    <table class="w-full text-left border-collapse">
                        <thead class="sticky top-0 bg-slate-900 border-b border-slate-800 text-[10px] font-bold text-slate-400 uppercase tracking-wider z-10">
                            <tr>
                                <th class="px-5 py-2.5">Log ID</th>
                                <th class="px-5 py-2.5">Name</th>
                                <th class="px-5 py-2.5">Scan Time</th>
                                <th class="px-5 py-2.5">Status</th>
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

# ================= PUBLIC MARK ATTENDANCE SCREEN =================
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

    # Public Interface Framework Styling Rules
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
    box-shadow: 0 20px 40px -15px rgba(0,0,0,0.5);
    """

    if not data:
        conn.close()
        return f"""
        <div style="{PAGE_BODY_STYLE}">
            <div style="{PANEL_CARD_STYLE}">
                <div style="color:#ef4444; font-size:44px; margin-bottom:14px;">✖</div>
                <h2 style="margin:0 0 6px 0; font-size:20px; font-weight:700;">Invalid Link</h2>
                <p style="color:#94a3b8; font-size:13px; line-height:1.5; margin:0;">This attendance tracking link is not valid or has expired.</p>
            </div>
        </div>
        """

    name = data[0]
    start_time = data[1]
    end_time = data[2]

    # Maintaining adjusted UTC timezone rules (+4 Hours)
    now = datetime.utcnow() + timedelta(hours=4)

    start_dt = datetime.strptime(start_time, "%Y-%m-%dT%H:%M")
    end_dt = datetime.strptime(end_time, "%Y-%m-%dT%H:%M")

    if now < start_dt:
        conn.close()
        return f"""
        <div style="{PAGE_BODY_STYLE}">
            <div style="{PANEL_CARD_STYLE}">
                <div style="color:#f59e0b; font-size:44px; margin-bottom:14px;">🛑</div>
                <h2 style="margin:0 0 6px 0; font-size:20px; font-weight:700;">Attendance Not Started</h2>
                <p style="color:#94a3b8; font-size:13px; margin:0 0 16px 0; line-height:1.5;">This attendance scanning window is not open yet.</p>
                <div style="background-color:#1e293b; padding:12px; border-radius:10px; font-family:monospace; font-size:12px; color:#94a3b8;">
                    Opens At: <br/><strong style="font-size:14px; color:#fff; display:block; margin-top:4px;">{start_dt.strftime('%Y-%m-%d %H:%M')}</strong>
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
                <h2 style="margin:0 0 6px 0; font-size:20px; font-weight:700;">Link Expired</h2>
                <p style="color:#94a3b8; font-size:13px; margin:0 0 16px 0; line-height:1.5;">The time limit to scan this QR code has already passed.</p>
                <div style="background-color:#1e293b; padding:12px; border-radius:10px; font-family:monospace; font-size:12px; color:#f43f5e;">
                    Closed At: <br/><strong style="font-size:14px; color:#fff; display:block; margin-top:4px;">{end_dt.strftime('%Y-%m-%d %H:%M')}</strong>
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
                <h2 style="margin:0 0 6px 0; font-size:20px; font-weight:700;">Already Marked</h2>
                <p style="color:#94a3b8; font-size:13px; margin:0 0 14px 0; line-height:1.5;">Your attendance has already been recorded for today.</p>
                <div style="border-top:1px solid #1e293b; padding-top:14px;">
                    <h3 style="color:#ffffff; margin:0; font-size:17px; font-weight:600;">{name}</h3>
                    <p style="color:#3b82f6; font-size:11px; text-transform:uppercase; font-weight:bold; margin-top:3px; letter-spacing:0.5px;">Status: Saved</p>
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
            <h2 style="margin:0 0 6px 0; font-size:20px; font-weight:700; color:#10b981;">Attendance Marked!</h2>
            <p style="color:#94a3b8; font-size:13px; margin:0 0 16px 0; line-height:1.5;">Your attendance has been recorded in the system.</p>
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
