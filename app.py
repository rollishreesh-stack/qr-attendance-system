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
matplotlib.use('Agg')  # Prevents GUI compilation issues on cloud servers
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

    # Setup default admin account if empty (User: admin / Pass: admin123)
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
        
        // Premium Accordion Toggle Animation
        function toggleSection(id) {
            const content = document.getElementById(id);
            const icon = document.getElementById('icon-' + id);
            
            if (content.classList.contains('hidden')) {
                content.classList.remove('hidden');
                setTimeout(() => {
                    content.classList.remove('opacity-0', '-translate-y-4');
                    content.classList.add('opacity-100', 'translate-y-0');
                }, 10);
                icon.classList.add('rotate-180');
            } else {
                content.classList.remove('opacity-100', 'translate-y-0');
                content.classList.add('opacity-0', '-translate-y-4');
                icon.classList.remove('rotate-180');
                setTimeout(() => {
                    content.classList.add('hidden');
                }, 200);
            }
        }
    </script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=Outfit:wght@300;400;500;600;700;800;900&display=swap');
        
        body { 
            font-family: 'Inter', sans-serif; 
            background-color: #030712; 
            background-image: radial-gradient(circle at 50% 0%, #111827 0%, transparent 70%);
            background-attachment: fixed;
        }
        
        h1, h2, h3, h4, .font-outfit {
            font-family: 'Outfit', sans-serif;
        }

        /* Premium Glass Panels */
        .glass-panel {
            background: rgba(17, 24, 39, 0.65);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.05);
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
        }

        /* Fast and smooth picture fade transition */
        .fade-transition {
            transition: opacity 0.5s ease-in-out;
        }
        
        .accordion-content {
            transition: all 0.2s ease-in-out;
        }
    </style>
</head>
<body class="text-slate-300 min-h-screen flex selection:bg-indigo-500 selection:text-white">

    {% if current_user.is_authenticated %}
    <!-- Sidebar Navigation -->
    <aside class="w-72 bg-[#090d16]/95 backdrop-blur-xl border-r border-slate-800/60 flex flex-col fixed h-full z-20 shadow-2xl">
        <div class="p-8 border-b border-slate-800/60 flex items-center gap-4">
            <div class="bg-gradient-to-br from-slate-700 to-slate-900 p-3 rounded-xl text-white border border-slate-600/30 shadow-lg">
                <i class="fa-solid fa-building-columns text-xl"></i>
            </div>
            <div>
                <h1 class="text-xl font-black text-white tracking-wider font-outfit">AIMCS</h1>
                <p class="text-[10px] text-slate-400 font-medium tracking-widest uppercase mt-0.5">Main Menu</p>
            </div>
        </div>
        
        <nav class="flex-1 p-5 space-y-1.5 mt-2">
            <a href="/" class="flex items-center gap-4 px-4 py-3 rounded-xl text-sm font-medium transition-all text-slate-400 hover:bg-slate-800/50 hover:text-white">
                <i class="fa-solid fa-house text-base w-6 text-center text-slate-500"></i> Home Gateway
            </a>
            <a href="/dashboard" class="flex items-center gap-4 px-4 py-3 rounded-xl text-sm font-medium transition-all text-slate-400 hover:bg-slate-800/50 hover:text-white">
                <i class="fa-solid fa-layer-group text-base w-6 text-center text-slate-400"></i> Dashboard
            </a>
            <a href="/bulk" class="flex items-center gap-4 px-4 py-3 rounded-xl text-sm font-medium transition-all text-slate-400 hover:bg-slate-800/50 hover:text-white">
                <i class="fa-solid fa-qrcode text-base w-6 text-center text-slate-400"></i> Create QR Codes
            </a>
            <a href="/analysis" class="flex items-center gap-4 px-4 py-3 rounded-xl text-sm font-medium transition-all text-slate-400 hover:bg-slate-800/50 hover:text-white">
                <i class="fa-solid fa-chart-line text-base w-6 text-center text-slate-400"></i> Analytics
            </a>
            <a href="/profile" class="flex items-center gap-4 px-4 py-3 rounded-xl text-sm font-medium transition-all text-slate-400 hover:bg-slate-800/50 hover:text-white">
                <i class="fa-solid fa-key text-base w-6 text-center text-slate-400"></i> Change Password
            </a>
            <div class="pt-4 mt-4 border-t border-slate-800/60">
                <a href="/logout" class="flex items-center gap-4 px-4 py-3 rounded-xl text-sm font-medium transition-all text-rose-400 hover:bg-rose-500/10 hover:text-rose-300">
                    <i class="fa-solid fa-power-off text-base w-6 text-center"></i> Logout
                </a>
            </div>
        </nav>

        <div class="p-6">
            <div class="glass-panel p-4 rounded-xl flex items-center gap-3 bg-slate-900/40">
                <div class="w-9 h-9 rounded-full bg-gradient-to-br from-slate-600 to-slate-800 text-white flex items-center justify-center font-bold text-sm border border-slate-700">
                    {{ current_user.username[0].upper() }}
                </div>
                <div class="truncate">
                    <p class="text-sm font-bold text-white truncate font-outfit">{{ current_user.username }}</p>
                    <p class="text-[10px] text-emerald-400 font-medium tracking-wide truncate">Administrator</p>
                </div>
            </div>
        </div>
    </aside>
    {% endif %}

    <!-- Main Application Panel -->
    <main class="flex-1 {% if current_user.is_authenticated %}pl-72{% endif %} min-h-screen flex flex-col relative z-10">
        <header class="h-20 bg-[#030712]/60 backdrop-blur-md border-b border-slate-800/60 flex items-center justify-between px-10 sticky top-0 z-30">
            <div class="flex items-center gap-2.5 bg-slate-900/60 px-3.5 py-1.5 rounded-full border border-slate-800/80">
                <span class="relative flex h-2 w-2">
                  <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span class="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                </span>
                <p class="text-[10px] font-bold tracking-wider text-slate-400 uppercase font-outfit">AIMCS System Online</p>
            </div>
            <div class="text-xs font-medium text-slate-300 flex items-center gap-2.5 glass-panel px-4 py-2 rounded-xl bg-slate-900/20">
                <i class="fa-regular fa-clock text-slate-400"></i> <span id="liveClock" class="font-mono tracking-wide"></span>
            </div>
        </header>

        <div class="p-8 flex-1 flex flex-col justify-start max-w-7xl mx-auto w-full">
            {{ content | safe }}
        </div>
    </main>

    <script>
        function updateClock() {
            const now = new Date();
            const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' };
            document.getElementById('liveClock').innerText = now.toLocaleDateString('en-US', options);
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
            error_msg = "Invalid username or password."

    content = f"""
    <div class="max-w-md w-full mx-auto my-auto glass-panel rounded-2xl p-8 space-y-6 relative overflow-hidden">
        
        <div class="text-center space-y-2 relative z-10">
            <div class="inline-flex p-3.5 bg-slate-800/60 text-slate-300 rounded-xl mb-2 border border-slate-700/50">
                <i class="fa-solid fa-lock text-3xl"></i>
            </div>
            <h2 class="text-2xl font-bold text-white tracking-tight font-outfit">Admin Sign In</h2>
            <p class="text-xs text-slate-400">Please enter your account details to access AIMCS.</p>
        </div>
        
        {f'<div class="p-3 bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs rounded-xl font-medium text-center"><i class="fa-solid fa-circle-exclamation mr-1.5"></i>{error_msg}</div>' if error_msg else ''}

        <form method="POST" class="space-y-4 relative z-10">
            <div class="space-y-1">
                <label class="text-[11px] font-bold text-slate-400 uppercase tracking-wide font-outfit">Username</label>
                <div class="relative">
                    <div class="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                        <i class="fa-solid fa-user text-xs"></i>
                    </div>
                    <input type="text" name="username" class="w-full bg-[#030712]/60 border border-slate-800 rounded-xl pl-10 pr-4 py-3 text-sm text-white focus:outline-none focus:border-slate-500 transition-all" placeholder="Enter username" required>
                </div>
            </div>
            <div class="space-y-1">
                <label class="text-[11px] font-bold text-slate-400 uppercase tracking-wide font-outfit">Password</label>
                <div class="relative">
                    <div class="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                        <i class="fa-solid fa-key text-xs"></i>
                    </div>
                    <input type="password" name="password" class="w-full bg-[#030712]/60 border border-slate-800 rounded-xl pl-10 pr-4 py-3 text-sm text-white focus:outline-none focus:border-slate-500 transition-all" placeholder="Enter password" required>
                </div>
            </div>
            <button type="submit" class="w-full inline-flex items-center justify-center px-4 py-3 bg-gradient-to-r from-slate-700 to-slate-800 hover:from-slate-600 hover:to-slate-700 border border-slate-600/30 text-white font-bold rounded-xl text-sm transition-all shadow-md">
                Sign In
            </button>
        </form>
    </div>
    """
    return render_template_string(LAYOUT_TEMPLATE, content=content)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

# ================= ACCOUNT SETTINGS =================
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
    <div class="max-w-xl mx-auto glass-panel rounded-2xl p-8 space-y-6">
        <div class="border-b border-slate-800/60 pb-4">
            <h2 class="text-2xl font-bold text-white tracking-tight font-outfit">Change Password</h2>
            <p class="text-xs text-slate-400 mt-1">Update your administrative access credentials.</p>
        </div>

        {status_msg}

        <form method="POST" class="space-y-4">
            <div class="space-y-1">
                <label class="text-[11px] font-bold text-slate-400 uppercase tracking-wide font-outfit">Current Password</label>
                <input type="password" name="old_password" class="w-full bg-[#030712]/60 border border-slate-800 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-slate-500 transition-all" required>
            </div>
            <div class="space-y-1">
                <label class="text-[11px] font-bold text-slate-400 uppercase tracking-wide font-outfit">New Password</label>
                <input type="password" name="new_password" class="w-full bg-[#030712]/60 border border-slate-800 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-slate-500 transition-all" required>
            </div>
            <button type="submit" class="w-full inline-flex items-center justify-center px-4 py-3 bg-slate-800 hover:bg-slate-700 text-white font-bold rounded-xl text-sm transition-all border border-slate-700">
                Save Changes
            </button>
        </form>
    </div>
    """
    return render_template_string(LAYOUT_TEMPLATE, content=content)

# ================= HOME (FAST PICTURES + PLATINUM BRANDING) =================
@app.route("/")
@login_required
def home():
    content = """
    <div class="w-full max-w-5xl mx-auto">
        
        <!-- Premium Home Gateway with Faster Slider Backdrops -->
        <div class="relative w-full h-[500px] rounded-2xl overflow-hidden border border-slate-800/60 shadow-2xl group">
            
            <!-- Highly accelerated background slider -->
            <div id="hero-slider-bg" class="absolute inset-0 bg-cover bg-center fade-transition opacity-30 scale-105 group-hover:scale-100 transition-transform duration-[4s]"></div>
            
            <!-- Dark Overlay -->
            <div class="absolute inset-0 bg-gradient-to-r from-[#030712] via-[#030712]/90 to-[#030712]/20"></div>
            
            <!-- Elegant Content Overlay -->
            <div class="relative z-10 h-full flex flex-col justify-center px-12 md:px-16 w-full md:w-4/5">
                
                <!-- Premium Platinum / Metallic Gradient Text matching picture tones -->
                <h2 class="text-7xl md:text-8xl font-black text-transparent bg-clip-text bg-gradient-to-b from-slate-100 via-slate-300 to-slate-500 tracking-wider font-outfit mb-1 drop-shadow-sm">
                    AIMCS
                </h2>
                <h3 class="text-xl md:text-2xl text-slate-300 font-light tracking-[0.25em] font-outfit mb-6 uppercase">
                    Attendance Platform
                </h3>
                
                <p class="text-sm md:text-base text-slate-400 max-w-lg leading-relaxed mb-8 font-light border-l border-slate-700 pl-4">
                    Create instant QR codes, track scan records in real-time, and download professional Excel reports instantly.
                </p>
                <div>
                    <a href="/dashboard" class="inline-flex items-center justify-center px-6 py-3 bg-slate-800 hover:bg-slate-700 text-white text-sm font-semibold rounded-xl transition-all border border-slate-700 shadow-md hover:-translate-y-0.5">
                        Open Dashboard <i class="fa-solid fa-arrow-right ml-2 text-xs"></i>
                    </a>
                </div>
            </div>
        </div>

        <script>
            // Premium background pictures (Office & Campus Vibe)
            const sliderImages = [
                'https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&q=80&w=1200',
                'https://images.unsplash.com/photo-1556761175-5973dc0f32b7?auto=format&fit=crop&q=80&w=1200',
                'https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&q=80&w=1200'
            ];
            
            let currentImageIdx = 0;
            const sliderElement = document.getElementById('hero-slider-bg');
            
            function changeSlide() {
                sliderElement.style.opacity = '0';
                
                setTimeout(() => {
                    sliderElement.style.backgroundImage = `url('${sliderImages[currentImageIdx]}')`;
                    sliderElement.style.opacity = '0.30'; 
                    currentImageIdx = (currentImageIdx + 1) % sliderImages.length;
                }, 500); // Shorter fade transition speed
            }

            // Load initial view
            sliderElement.style.backgroundImage = `url('${sliderImages[0]}')`;
            sliderElement.style.opacity = '0.30';
            currentImageIdx = 1;
            
            // Much faster slide changing loop
            setInterval(changeSlide, 2500);
        </script>
    </div>
    """
    return render_template_string(LAYOUT_TEMPLATE, content=content)

# ================= DASHBOARD (CLEAN DROPDOWNS) =================
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
    <div class="space-y-4 w-full max-w-5xl mx-auto">
        
        <div class="mb-6">
            <h2 class="text-3xl font-bold text-white tracking-tight font-outfit">System Dashboard</h2>
            <p class="text-xs text-slate-400 mt-1">Quick summary of registered records and management shortcuts.</p>
        </div>

        <!-- Section 1: Statistics Dropdown -->
        <div class="glass-panel rounded-2xl overflow-hidden border border-slate-800/60">
            <button onclick="toggleSection('sect-telemetry')" class="w-full px-6 py-4.5 flex items-center justify-between bg-slate-900/40 hover:bg-slate-800/30 transition-colors border-l-2 border-slate-400 focus:outline-none">
                <div class="flex items-center gap-3">
                    <span class="text-sm font-bold text-white tracking-wider font-outfit uppercase">Platform Statistics</span>
                </div>
                <i id="icon-sect-telemetry" class="fa-solid fa-chevron-down text-slate-400 transition-transform duration-200 rotate-180"></i>
            </button>
            
            <div id="sect-telemetry" class="px-6 py-6 accordion-content opacity-100 translate-y-0">
                <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div class="bg-[#030712]/40 border border-slate-800 p-6 rounded-xl flex items-center justify-between">
                        <div class="space-y-1">
                            <p class="text-[10px] font-bold tracking-wider text-slate-400 uppercase font-outfit">Registered Students</p>
                            <h3 class="text-3xl font-bold text-white tracking-tight font-outfit">{students}</h3>
                        </div>
                        <div class="text-slate-500 text-2xl"><i class="fa-solid fa-users"></i></div>
                    </div>

                    <div class="bg-[#030712]/40 border border-slate-800 p-6 rounded-xl flex items-center justify-between">
                        <div class="space-y-1">
                            <p class="text-[10px] font-bold tracking-wider text-slate-400 uppercase font-outfit">Total Attendance Logs</p>
                            <h3 class="text-3xl font-bold text-white tracking-tight font-outfit">{attendance}</h3>
                        </div>
                        <div class="text-slate-500 text-2xl"><i class="fa-solid fa-circle-check"></i></div>
                    </div>

                    <div class="bg-[#030712]/40 border border-slate-800 p-6 rounded-xl flex items-center justify-between">
                        <div class="space-y-1">
                            <p class="text-[10px] font-bold tracking-wider text-slate-400 uppercase font-outfit">System Status</p>
                            <h3 class="text-base font-bold text-emerald-400 tracking-tight font-outfit mt-1">Operational</h3>
                        </div>
                        <div class="text-emerald-600 text-xl"><i class="fa-solid fa-server"></i></div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Section 2: Management Tools Dropdown -->
        <div class="glass-panel rounded-2xl overflow-hidden border border-slate-800/60">
            <button onclick="toggleSection('sect-admin')" class="w-full px-6 py-4.5 flex items-center justify-between bg-slate-900/40 hover:bg-slate-800/30 transition-colors border-l-2 border-slate-400 focus:outline-none">
                <div class="flex items-center gap-3">
                    <span class="text-sm font-bold text-white tracking-wider font-outfit uppercase">Quick Tools</span>
                </div>
                <i id="icon-sect-admin" class="fa-solid fa-chevron-down text-slate-400 transition-transform duration-200 rotate-180"></i>
            </button>
            
            <div id="sect-admin" class="px-6 py-6 accordion-content opacity-100 translate-y-0">
                <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    <a href="/bulk" class="flex flex-col items-center justify-center p-6 bg-[#030712]/40 hover:bg-slate-800/40 rounded-xl border border-slate-800 text-center group transition-all">
                        <i class="fa-solid fa-qrcode text-2xl text-slate-400 mb-2 group-hover:scale-105 transition-transform"></i>
                        <span class="text-xs font-semibold text-white">Create QR Codes</span>
                    </a>
                    <a href="/download" class="flex flex-col items-center justify-center p-6 bg-[#030712]/40 hover:bg-slate-800/40 rounded-xl border border-slate-800 text-center group transition-all">
                        <i class="fa-solid fa-file-excel text-2xl text-slate-400 mb-2 group-hover:scale-105 transition-transform"></i>
                        <span class="text-xs font-semibold text-white">Export Excel Sheet</span>
                    </a>
                    <a href="/download_qrs" class="flex flex-col items-center justify-center p-6 bg-[#030712]/40 hover:bg-slate-800/40 rounded-xl border border-slate-800 text-center group transition-all">
                        <i class="fa-solid fa-file-zipper text-2xl text-slate-400 mb-2 group-hover:scale-105 transition-transform"></i>
                        <span class="text-xs font-semibold text-white">Download All QRs (.zip)</span>
                    </a>
                </div>
            </div>
        </div>

    </div>
    """
    return render_template_string(LAYOUT_TEMPLATE, content=content)

# ================= BULK QR CREATOR =================
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
                print("Error saving line data:", e)

        conn.commit()
        conn.close()

        js_data = "\n".join(js_students)

        content = f"""
        <div class="max-w-2xl mx-auto glass-panel rounded-2xl p-10 text-center space-y-6">
            <div class="inline-flex p-4 bg-emerald-500/10 text-emerald-400 rounded-full border border-emerald-500/20">
                <i class="fa-solid fa-circle-check text-4xl"></i>
            </div>
            <h2 class="text-2xl font-bold text-white tracking-tight font-outfit">QR Codes Generated!</h2>
            <p class="text-slate-400 text-sm max-w-md mx-auto leading-relaxed">
                Successfully processed <span class="text-white font-bold">{success}</span> student profile(s). The system is now emailing the QR codes to the students in the background.
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

            <div class="pt-6 border-t border-slate-800">
                <a href='/dashboard' class="inline-flex items-center justify-center px-6 py-2.5 bg-slate-800 hover:bg-slate-700 text-white text-xs font-semibold rounded-xl border border-slate-700">
                    Return to Dashboard
                </a>
            </div>
        </div>
        """
        return render_template_string(LAYOUT_TEMPLATE, content=content)

    content = """
    <div class="max-w-3xl mx-auto glass-panel rounded-2xl p-8 space-y-6">
        <div class="border-b border-slate-800/60 pb-4">
            <h2 class="text-2xl font-bold text-white tracking-tight font-outfit">Generate QR Codes in Bulk</h2>
            <p class="text-xs text-slate-400 mt-1">Set the activation hours and input your list of names and emails.</p>
        </div>

        <form method='POST' class="space-y-6">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div class="space-y-1">
                    <label class='text-[11px] font-bold text-slate-400 uppercase tracking-wide font-outfit'>Start Date & Time</label>
                    <input type='datetime-local' name='start_time' class='w-full bg-[#030712]/60 border border-slate-800 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-slate-500 transition-all' required>
                </div>
                <div class="space-y-1">
                    <label class='text-[11px] font-bold text-slate-400 uppercase tracking-wide font-outfit'>End Date & Time</label>
                    <input type='datetime-local' name='end_time' class='w-full bg-[#030712]/60 border border-slate-800 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-slate-500 transition-all' required>
                </div>
            </div>

            <div class="space-y-1">
                <label class='text-[11px] font-bold text-slate-400 uppercase tracking-wide font-outfit'>Student List (Format: Name, Email)</label>
                <div class="relative">
                    <textarea name='data' class='w-full h-48 bg-[#030712]/60 border border-slate-800 rounded-xl p-4 text-xs text-white focus:outline-none focus:border-slate-500 transition-all font-mono leading-relaxed' placeholder="Alexander Pierce, alex@example.com&#10;Sophia Chen, sophia@example.com" required></textarea>
                </div>
                <p class="text-[11px] text-slate-500 italic mt-1">Note: Enter each student on a separate line with a comma between the name and email address.</p>
            </div>
            
            <button type='submit' class="w-full inline-flex items-center justify-center px-4 py-3 bg-slate-800 hover:bg-slate-700 text-white font-bold rounded-xl text-sm border border-slate-700 shadow-md">
                Generate & Send QR Codes
            </button>
        </form>
    </div>
    """
    return render_template_string(LAYOUT_TEMPLATE, content=content)

# ================= ANALYTICS & LEDGERS =================
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

            plt.figure(figsize=(9, 3.5))
            plt.gcf().patch.set_facecolor('#111827')
            plt.gcf().patch.set_alpha(0.0) 
            ax = plt.gca()
            ax.set_facecolor('#111827')
            ax.patch.set_alpha(0.0)
            
            bars = attendance_counts.plot(kind='bar', color='#64748b', width=0.35, ax=ax)
            
            ax.tick_params(colors='#94a3b8', labelsize=9)
            ax.spines['bottom'].set_color('#334155')
            ax.spines['left'].set_color('#334155')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.grid(axis='y', color='#334155', linestyle='--', alpha=0.2)
            
            plt.title("Attendance Frequency Chart", color='#f8fafc', fontsize=12, pad=12, weight='bold')
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            
            img_buf = io.BytesIO()
            plt.savefig(img_buf, format='png', transparent=True, bbox_inches='tight')
            img_buf.seek(0)
            import base64
            chart_url = "data:image/png;base64," + base64.b64encode(img_buf.getvalue()).decode('utf-8')
            plt.close()
        except Exception as e:
            print("Chart building error layout:", e)

    table_rows = ""
    if not df_logs.empty:
        for idx, row in df_logs.iterrows():
            table_rows += f"""
            <tr class="border-b border-slate-800/60 text-slate-300 text-xs hover:bg-slate-800/20">
                <td class="px-5 py-3 font-mono text-slate-500">#{row['id']}</td>
                <td class="px-5 py-3 font-semibold text-white">{row['name']}</td>
                <td class="px-5 py-3 font-mono text-slate-400">{row['time']}</td>
                <td class="px-5 py-3"><span class="px-2 py-0.5 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-full text-[10px] font-semibold uppercase">Verified</span></td>
            </tr>
            """
    else:
        table_rows = """
        <tr>
            <td colspan="4" class="px-5 py-10 text-center text-xs text-slate-500 font-medium">No attendance logs available in the system yet.</td>
        </tr>
        """

    content = f"""
    <div class="space-y-4 w-full max-w-5xl mx-auto">
        
        <div class="mb-6">
            <h2 class="text-3xl font-bold text-white tracking-tight font-outfit">Attendance Analytics</h2>
            <p class="text-xs text-slate-400 mt-1">View tracking graphs, registered lists, and live logs inside clean dropdown blocks.</p>
        </div>

        <!-- Section 1: Visual Graph Dropdown -->
        <div class="glass-panel rounded-2xl overflow-hidden border border-slate-800/60">
            <button onclick="toggleSection('sect-chart')" class="w-full px-6 py-4.5 flex items-center justify-between bg-slate-900/40 hover:bg-slate-800/30 transition-colors border-l-2 border-slate-400 focus:outline-none">
                <div class="flex items-center gap-3">
                    <span class="text-sm font-bold text-white tracking-wider font-outfit uppercase">Attendance Timeline Graph</span>
                </div>
                <i id="icon-sect-chart" class="fa-solid fa-chevron-down text-slate-400 transition-transform duration-200 rotate-180"></i>
            </button>
            <div id="sect-chart" class="px-6 py-6 accordion-content opacity-100 translate-y-0">
                <div class="bg-[#030712]/40 border border-slate-800 rounded-xl p-4 flex items-center justify-center">
                    {f'<img src="{chart_url}" class="w-full max-w-3xl drop-shadow-xl" />' if chart_url else '<div class="text-slate-500 text-xs text-center py-12">Not enough data to create a graph view yet.</div>'}
                </div>
            </div>
        </div>

        <!-- Section 2: Active Student Profiles Dropdown -->
        <div class="glass-panel rounded-2xl overflow-hidden border border-slate-800/60">
            <button onclick="toggleSection('sect-matrix')" class="w-full px-6 py-4.5 flex items-center justify-between bg-slate-900/40 hover:bg-slate-800/30 transition-colors border-l-2 border-slate-400 focus:outline-none">
                <div class="flex items-center gap-3">
                    <span class="text-sm font-bold text-white tracking-wider font-outfit uppercase">Registered Student List</span>
                </div>
                <i id="icon-sect-matrix" class="fa-solid fa-chevron-down text-slate-400 transition-transform duration-200"></i>
            </button>
            <div id="sect-matrix" class="px-6 py-6 accordion-content hidden opacity-0 -translate-y-4">
                <div class="overflow-x-auto rounded-xl border border-slate-800 bg-[#030712]/40">
                    <table class="w-full text-left border-collapse">
                        <thead>
                            <tr class="bg-slate-900/80 border-b border-slate-800 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                                <th class="px-5 py-3">No.</th>
                                <th class="px-5 py-3">Student Name</th>
                                <th class="px-5 py-3">Active Validity Hours</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-slate-800/40 text-xs text-slate-300">
                            {"".join([f'<tr><td class="px-5 py-3 font-mono text-slate-500">#{i+1}</td><td class="px-5 py-3 font-semibold text-white">{r["name"]}</td><td class="px-5 py-3 font-mono text-slate-400">{r["start_time"]} to {r["end_time"]}</td></tr>' for i, r in df_config.iterrows()]) if not df_config.empty else '<tr><td colspan="3" class="px-5 py-6 text-center text-slate-500">No active students found.</td></tr>'}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- Section 3: Ingestion Log Dropdown -->
        <div class="glass-panel rounded-2xl overflow-hidden border border-slate-800/60">
            <button onclick="toggleSection('sect-ledger')" class="w-full px-6 py-4.5 flex items-center justify-between bg-slate-900/40 hover:bg-slate-800/30 transition-colors border-l-2 border-slate-400 focus:outline-none">
                <div class="flex items-center gap-3">
                    <span class="text-sm font-bold text-white tracking-wider font-outfit uppercase">Live Attendance Log</span>
                </div>
                <i id="icon-sect-ledger" class="fa-solid fa-chevron-down text-slate-400 transition-transform duration-200"></i>
            </button>
            <div id="sect-ledger" class="px-6 py-6 accordion-content hidden opacity-0 -translate-y-4">
                <div class="overflow-hidden border border-slate-800 rounded-xl bg-[#030712]/40">
                    <div class="max-h-72 overflow-y-auto">
                        <table class="w-full text-left border-collapse">
                            <thead class="sticky top-0 bg-slate-900 border-b border-slate-800 text-[10px] font-bold text-slate-400 uppercase tracking-wider z-10">
                                <tr>
                                    <th class="px-5 py-3">Log ID</th>
                                    <th class="px-5 py-3">Name</th>
                                    <th class="px-5 py-3">Scan Time</th>
                                    <th class="px-5 py-3">Status</th>
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
    </div>
    """
    return render_template_string(LAYOUT_TEMPLATE, content=content)

# ================= PUBLIC SIGN-IN ENDPOINT (SCANNED QR) =================
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

    # Public Mobile Screen Styling
    BASE_PUBLIC_STYLE = """
    font-family: 'Inter', system-ui, sans-serif; 
    text-align:center; 
    padding:80px 16px; 
    background-color:#030712; 
    background-image: radial-gradient(circle at 50% 0%, #111827 0%, transparent 70%);
    color:#f8fafc; 
    min-height:100vh; 
    box-sizing:border-box;
    display: flex;
    align-items: center;
    justify-content: center;
    """
    
    CARD_STYLE = """
    max-width:480px; 
    width: 100%;
    background: rgba(17, 24, 39, 0.75);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border:1px solid rgba(255,255,255,0.05); 
    padding:40px 24px; 
    border-radius:24px; 
    box-shadow:0 25px 50px -12px rgba(0, 0, 0, 0.5);
    """

    if not data:
        conn.close()
        return f"""
        <div style="{BASE_PUBLIC_STYLE}">
            <div style="{CARD_STYLE}">
                <div style="color:#ef4444; font-size:48px; margin-bottom:16px;">✖</div>
                <h2 style="margin:0 0 8px 0; font-size:22px; font-weight:700;">Invalid Link</h2>
                <p style="color:#94a3b8; font-size:14px; line-height:1.5; margin:0;">This attendance link is incorrect or has been altered.</p>
            </div>
        </div>
        """

    name = data[0]
    start_time = data[1]
    end_time = data[2]

    # Timezone conversion (+4 Hours over UTC)
    now = datetime.utcnow() + timedelta(hours=4)

    start_dt = datetime.strptime(start_time, "%Y-%m-%dT%H:%M")
    end_dt = datetime.strptime(end_time, "%Y-%m-%dT%H:%M")

    if now < start_dt:
        conn.close()
        return f"""
        <div style="{BASE_PUBLIC_STYLE}">
            <div style="{CARD_STYLE}">
                <div style="color:#f59e0b; font-size:48px; margin-bottom:16px;">🛑</div>
                <h2 style="margin:0 0 8px 0; font-size:22px; font-weight:700;">Attendance Not Started</h2>
                <p style="color:#94a3b8; font-size:14px; margin:0 0 20px 0; line-height:1.5;">This tracking window is not active yet.</p>
                <div style="background-color:rgba(30, 41, 59, 0.4); padding:14px; border-radius:12px; font-family:monospace; font-size:13px; color:#94a3b8; border:1px solid rgba(255,255,255,0.05);">
                    Opens At: <br/><strong style="font-size:15px; color:#fff; display:block; margin-top:4px;">{start_dt.strftime('%Y-%m-%d %H:%M')}</strong>
                </div>
            </div>
        </div>
        """

    if now > end_dt:
        conn.close()
        return f"""
        <div style="{BASE_PUBLIC_STYLE}">
            <div style="{CARD_STYLE}">
                <div style="color:#ef4444; font-size:48px; margin-bottom:16px;">⚠️</div>
                <h2 style="margin:0 0 8px 0; font-size:22px; font-weight:700;">Link Expired</h2>
                <p style="color:#94a3b8; font-size:14px; margin:0 0 20px 0; line-height:1.5;">The time window for this attendance check has already ended.</p>
                <div style="background-color:rgba(30, 41, 59, 0.4); padding:14px; border-radius:12px; font-family:monospace; font-size:13px; color:#f43f5e; border:1px solid rgba(244, 63, 94, 0.1);">
                    Closed At: <br/><strong style="font-size:15px; color:#fff; display:block; margin-top:4px;">{end_dt.strftime('%Y-%m-%d %H:%M')}</strong>
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
        <div style="{BASE_PUBLIC_STYLE}">
            <div style="{CARD_STYLE}">
                <div style="color:#3b82f6; font-size:48px; margin-bottom:16px;">🔁</div>
                <h2 style="margin:0 0 8px 0; font-size:22px; font-weight:700;">Already Marked</h2>
                <p style="color:#94a3b8; font-size:14px; margin:0 0 16px 0; line-height:1.5;">Your check-in session has already been saved for today.</p>
                <div style="border-top:1px solid rgba(255,255,255,0.05); padding-top:16px;">
                    <h3 style="color:#ffffff; margin:0; font-size:18px; font-weight:600;">{name}</h3>
                    <p style="color:#3b82f6; font-size:11px; text-transform:uppercase; letter-spacing:1px; margin-top:4px; font-weight:bold;">Status: Safe</p>
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
    <div style="{BASE_PUBLIC_STYLE}">
        <div style="{CARD_STYLE}">
            <div style="color:#10b981; font-size:48px; margin-bottom:16px;">✅</div>
            <h2 style="margin:0 0 8px 0; font-size:22px; font-weight:700; color:#10b981;">Attendance Marked!</h2>
            <p style="color:#94a3b8; font-size:14px; margin:0 0 20px 0; line-height:1.5;">Your attendance has been successfully recorded in the system logs.</p>
            <div style="background:rgba(16,185,129,0.05); border:1px solid rgba(16,185,129,0.15); padding:16px; border-radius:12px;">
                <h3 style="color:#ffffff; margin:0; font-size:18px; font-weight:600;">{name}</h3>
                <p style="color:#10b981; font-size:12px; font-family:monospace; margin-top:4px; font-weight:bold;">{time_str}</p>
            </div>
        </div>
    </div>
    """

# ================= DOCUMENT DOWNLOAD ROUTS =================
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
