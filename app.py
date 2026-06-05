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
matplotlib.use('Agg')  # Prevents GUI compilation issues on Render
import matplotlib.pyplot as plt

app = Flask(__name__)
app.secret_key = "supersecretkey"

DB_NAME = "attendance.db"

# ================= DATABASE =================
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
    <title>AIMCS | Executive Attendance System</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <script src="https://cdn.jsdelivr.net/npm/@emailjs/browser@4/dist/email.min.js"></script>
    <script>
        (function(){
            emailjs.init("-oGl3hn1HEMpvxh2T");
        })();
    </script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=Outfit:wght@300;400;500;600;700;800&display=swap');
        
        body { 
            font-family: 'Inter', sans-serif; 
            background-color: #030712; /* Deep executive black */
            background-image: radial-gradient(circle at 50% 0%, #1e1b4b 0%, transparent 70%);
            background-attachment: fixed;
        }
        
        h1, h2, h3, h4, .font-outfit {
            font-family: 'Outfit', sans-serif;
        }

        /* Glassmorphism utilities */
        .glass-panel {
            background: rgba(17, 24, 39, 0.6);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.05);
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
        }

        /* Smooth fade animation for slider */
        .fade-transition {
            transition: opacity 1.5s ease-in-out;
        }
    </style>
</head>
<body class="text-slate-300 min-h-screen flex selection:bg-indigo-500 selection:text-white">

    {% if current_user.is_authenticated %}
    <aside class="w-72 bg-[#0a0a0a]/90 backdrop-blur-xl border-r border-slate-800/50 flex flex-col fixed h-full z-20 transition-all duration-300 shadow-2xl">
        <div class="p-8 border-b border-slate-800/50 flex items-center gap-4">
            <div class="bg-gradient-to-br from-indigo-500 to-blue-700 p-3 rounded-xl text-white shadow-[0_0_20px_rgba(79,70,229,0.3)]">
                <i class="fa-solid fa-building-columns text-xl"></i>
            </div>
            <div>
                <h1 class="text-xl font-extrabold text-white tracking-widest font-outfit">AIMCS</h1>
                <p class="text-[10px] text-indigo-400 font-semibold tracking-widest uppercase mt-1">Executive Core</p>
            </div>
        </div>
        
        <nav class="flex-1 p-5 space-y-2 mt-2">
            <a href="/" class="flex items-center gap-4 px-4 py-3.5 rounded-xl text-sm font-medium transition-all text-slate-400 hover:bg-slate-800/40 hover:text-white hover:shadow-lg">
                <i class="fa-solid fa-house text-lg w-6 text-center text-slate-500"></i> Home Gateway
            </a>
            <a href="/dashboard" class="flex items-center gap-4 px-4 py-3.5 rounded-xl text-sm font-medium transition-all text-slate-400 hover:bg-slate-800/40 hover:text-white hover:shadow-lg">
                <i class="fa-solid fa-chart-pie text-lg w-6 text-center text-indigo-400"></i> Analytics Dashboard
            </a>
            <a href="/bulk" class="flex items-center gap-4 px-4 py-3.5 rounded-xl text-sm font-medium transition-all text-slate-400 hover:bg-slate-800/40 hover:text-white hover:shadow-lg">
                <i class="fa-solid fa-qrcode text-lg w-6 text-center text-emerald-400"></i> Bulk QR Engine
            </a>
            <a href="/analysis" class="flex items-center gap-4 px-4 py-3.5 rounded-xl text-sm font-medium transition-all text-slate-400 hover:bg-slate-800/40 hover:text-white hover:shadow-lg">
                <i class="fa-solid fa-chart-line text-lg w-6 text-center text-blue-400"></i> Performance Report
            </a>
            <a href="/profile" class="flex items-center gap-4 px-4 py-3.5 rounded-xl text-sm font-medium transition-all text-slate-400 hover:bg-slate-800/40 hover:text-white hover:shadow-lg">
                <i class="fa-solid fa-user-shield text-lg w-6 text-center text-amber-400"></i> Security Settings
            </a>
            <div class="pt-4 mt-4 border-t border-slate-800/50">
                <a href="/logout" class="flex items-center gap-4 px-4 py-3.5 rounded-xl text-sm font-medium transition-all text-rose-400 hover:bg-rose-500/10 hover:text-rose-300">
                    <i class="fa-solid fa-power-off text-lg w-6 text-center"></i> Terminate Session
                </a>
            </div>
        </nav>

        <div class="p-6">
            <div class="glass-panel p-4 rounded-xl flex items-center gap-3">
                <div class="w-10 h-10 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 text-white flex items-center justify-center font-bold text-sm shadow-inner">
                    {{ current_user.username[0].upper() }}
                </div>
                <div class="truncate">
                    <p class="text-sm font-bold text-white truncate font-outfit">{{ current_user.username }}</p>
                    <p class="text-[10px] text-emerald-400 font-mono tracking-wider truncate">SysAdmin Online</p>
                </div>
            </div>
        </div>
    </aside>
    {% endif %}

    <main class="flex-1 {% if current_user.is_authenticated %}pl-72{% endif %} min-h-screen flex flex-col relative z-10">
        <header class="h-24 bg-[#030712]/70 backdrop-blur-xl border-b border-slate-800/50 flex items-center justify-between px-10 sticky top-0 z-30">
            <div class="flex items-center gap-3 bg-slate-900/50 px-4 py-2 rounded-full border border-slate-800">
                <span class="relative flex h-3 w-3">
                  <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
                  <span class="relative inline-flex rounded-full h-3 w-3 bg-indigo-500"></span>
                </span>
                <p class="text-[11px] font-bold tracking-widest text-slate-300 uppercase font-outfit">AIMCS Operational</p>
            </div>
            <div class="text-sm font-medium text-slate-300 flex items-center gap-3 glass-panel px-5 py-2.5 rounded-xl">
                <i class="fa-regular fa-clock text-indigo-400"></i> <span id="liveClock" class="font-mono tracking-wider text-xs"></span>
            </div>
        </header>

        <div class="p-10 flex-1 flex flex-col justify-start max-w-7xl mx-auto w-full">
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
            error_msg = "Invalid systemic credential mappings."

    content = f"""
    <div class="max-w-lg w-full mx-auto my-auto glass-panel rounded-3xl p-10 space-y-8 relative overflow-hidden">
        <div class="absolute -top-20 -right-20 w-64 h-64 bg-indigo-500/20 rounded-full blur-3xl"></div>
        
        <div class="text-center space-y-3 relative z-10">
            <div class="inline-flex p-4 bg-gradient-to-br from-indigo-500/20 to-blue-600/20 text-indigo-400 rounded-2xl mb-4 border border-indigo-500/30">
                <i class="fa-solid fa-fingerprint text-4xl"></i>
            </div>
            <h2 class="text-3xl font-extrabold text-white tracking-tight font-outfit">Executive Access</h2>
            <p class="text-sm text-slate-400">Authenticate to access AIMCS administration layers.</p>
        </div>
        
        {f'<div class="p-4 bg-rose-500/10 border border-rose-500/30 text-rose-400 text-sm rounded-xl font-medium text-center relative z-10"><i class="fa-solid fa-triangle-exclamation mr-2"></i>{error_msg}</div>' if error_msg else ''}

        <form method="POST" class="space-y-5 relative z-10">
            <div class="space-y-2">
                <label class="text-xs font-bold text-slate-400 uppercase tracking-widest font-outfit">Identification ID</label>
                <div class="relative">
                    <div class="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                        <i class="fa-solid fa-user text-slate-500 text-sm"></i>
                    </div>
                    <input type="text" name="username" class="w-full bg-[#030712]/50 border border-slate-700/50 rounded-xl pl-11 pr-4 py-3.5 text-sm text-white focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all" placeholder="e.g. admin" required>
                </div>
            </div>
            <div class="space-y-2">
                <label class="text-xs font-bold text-slate-400 uppercase tracking-widest font-outfit">Security Passphrase</label>
                <div class="relative">
                    <div class="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                        <i class="fa-solid fa-lock text-slate-500 text-sm"></i>
                    </div>
                    <input type="password" name="password" class="w-full bg-[#030712]/50 border border-slate-700/50 rounded-xl pl-11 pr-4 py-3.5 text-sm text-white focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all" placeholder="••••••••" required>
                </div>
            </div>
            <button type="submit" class="w-full inline-flex items-center justify-center px-4 py-4 bg-gradient-to-r from-indigo-600 to-blue-700 hover:from-indigo-500 hover:to-blue-600 text-white font-bold rounded-xl text-sm transition-all shadow-[0_0_20px_rgba(79,70,229,0.4)] hover:shadow-[0_0_30px_rgba(79,70,229,0.6)] hover:-translate-y-0.5">
                Authenticate Session <i class="fa-solid fa-arrow-right-to-bracket ml-2"></i>
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
            status_msg = """<div class="p-4 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-sm rounded-xl font-medium text-center"><i class="fa-solid fa-check-circle mr-2"></i>Cryptographic passphrase mutation complete.</div>"""
        else:
            status_msg = """<div class="p-4 bg-rose-500/10 border border-rose-500/30 text-rose-400 text-sm rounded-xl font-medium text-center"><i class="fa-solid fa-triangle-exclamation mr-2"></i>Root verification mismatch. Verification aborted.</div>"""
        conn.close()

    content = f"""
    <div class="max-w-2xl mx-auto glass-panel rounded-3xl p-10 space-y-8">
        <div class="border-b border-slate-800/50 pb-6">
            <h2 class="text-3xl font-extrabold text-white tracking-tight font-outfit">Security Protocol</h2>
            <p class="text-sm text-slate-400 mt-2">Alter administrative access credentials securely.</p>
        </div>

        {status_msg}

        <form method="POST" class="space-y-6">
            <div class="space-y-2">
                <label class="text-xs font-bold text-slate-400 uppercase tracking-widest font-outfit">Current Passphrase</label>
                <input type="password" name="old_password" class="w-full bg-[#030712]/50 border border-slate-700/50 rounded-xl px-5 py-3.5 text-sm text-white focus:outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500 transition-all" required>
            </div>
            <div class="space-y-2">
                <label class="text-xs font-bold text-slate-400 uppercase tracking-widest font-outfit">New Core Passphrase</label>
                <input type="password" name="new_password" class="w-full bg-[#030712]/50 border border-slate-700/50 rounded-xl px-5 py-3.5 text-sm text-white focus:outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500 transition-all" required>
            </div>
            <button type="submit" class="w-full inline-flex items-center justify-center px-4 py-4 bg-gradient-to-r from-amber-600 to-orange-600 hover:from-amber-500 hover:to-orange-500 text-white font-bold rounded-xl text-sm transition-all shadow-[0_0_20px_rgba(245,158,11,0.3)]">
                Commit Cryptographic Changes <i class="fa-solid fa-shield-check ml-2"></i>
            </button>
        </form>
    </div>
    """
    return render_template_string(LAYOUT_TEMPLATE, content=content)

# ================= HOME (WITH MOTION SLIDER) =================
@app.route("/")
@login_required
def home():
    content = """
    <div class="w-full max-w-6xl mx-auto flex flex-col gap-8">
        
        <div class="relative w-full h-[500px] rounded-3xl overflow-hidden border border-slate-700/50 shadow-2xl group">
            
            <div id="hero-slider-bg" class="absolute inset-0 bg-cover bg-center fade-transition opacity-50 scale-105 group-hover:scale-100 transition-transform duration-[10s]"></div>
            
            <div class="absolute inset-0 bg-gradient-to-r from-[#030712] via-[#030712]/80 to-transparent"></div>
            
            <div class="relative z-10 h-full flex flex-col justify-center px-12 md:px-20 w-full md:w-3/4">
                <div class="inline-flex p-4 bg-indigo-500/20 text-indigo-400 rounded-2xl border border-indigo-500/30 backdrop-blur-md mb-6 w-fit shadow-[0_0_30px_rgba(79,70,229,0.3)]">
                    <i class="fa-solid fa-network-wired text-4xl"></i>
                </div>
                <h2 class="text-5xl md:text-6xl font-extrabold text-white tracking-tight font-outfit mb-6 leading-tight">
                    Next-Gen <span class="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-blue-400">Attendance</span> Architecture.
                </h2>
                <p class="text-lg text-slate-300 max-w-2xl leading-relaxed mb-8 font-light">
                    Instantaneous encrypted tracking, automated structural reporting, and granular lifecycle auditing workflows engineered for modern institutions.
                </p>
                <div class="flex gap-4">
                    <a href="/dashboard" class="inline-flex items-center justify-center px-8 py-4 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-xl transition-all shadow-[0_0_20px_rgba(79,70,229,0.4)] hover:-translate-y-1">
                        Initialize Dashboard <i class="fa-solid fa-arrow-right ml-2 text-sm"></i>
                    </a>
                </div>
            </div>
        </div>

        <script>
            // Executive Motion Pictures Slider Logic
            const sliderImages = [
                'https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&q=80&w=1600', // Modern Office/Campus
                'https://images.unsplash.com/photo-1556761175-5973dc0f32b7?auto=format&fit=crop&q=80&w=1600', // Tech Environment
                'https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&q=80&w=1600'  // Abstract Network
            ];
            
            let currentImageIdx = 0;
            const sliderElement = document.getElementById('hero-slider-bg');
            
            function changeSlide() {
                sliderElement.style.opacity = '0';
                
                setTimeout(() => {
                    sliderElement.style.backgroundImage = `url('${sliderImages[currentImageIdx]}')`;
                    sliderElement.style.opacity = '0.4'; // Maintain subtle opacity behind text
                    currentImageIdx = (currentImageIdx + 1) % sliderImages.length;
                }, 1500); // Wait for fade out
            }

            // Initialize first image immediately
            sliderElement.style.backgroundImage = `url('${sliderImages[0]}')`;
            sliderElement.style.opacity = '0.4';
            currentImageIdx = 1;
            
            // Start interval
            setInterval(changeSlide, 6000);
        </script>
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
    <div class="space-y-8 w-full max-w-7xl mx-auto">
        <div class="border-b border-slate-800/50 pb-6 flex items-center justify-between">
            <div>
                <h2 class="text-3xl font-extrabold text-white tracking-tight font-outfit">Command Center</h2>
                <p class="text-sm text-slate-400 mt-1">Real-time telemetry and infrastructure utilization.</p>
            </div>
            <div class="px-4 py-2 bg-indigo-500/10 border border-indigo-500/20 rounded-lg text-indigo-400 text-xs font-bold tracking-widest uppercase">
                Status: Optimal
            </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <div class="glass-panel p-8 rounded-3xl flex items-center justify-between group hover:border-indigo-500/50 transition-colors">
                <div class="space-y-2">
                    <p class="text-xs font-bold tracking-widest text-slate-400 uppercase font-outfit">Registered Entities</p>
                    <h3 class="text-5xl font-extrabold text-white tracking-tight font-outfit">{students}</h3>
                </div>
                <div class="h-16 w-16 bg-gradient-to-br from-indigo-500/20 to-blue-500/20 border border-indigo-500/30 text-indigo-400 rounded-2xl flex items-center justify-center text-3xl group-hover:scale-110 transition-transform">
                    <i class="fa-solid fa-users"></i>
                </div>
            </div>

            <div class="glass-panel p-8 rounded-3xl flex items-center justify-between group hover:border-emerald-500/50 transition-colors">
                <div class="space-y-2">
                    <p class="text-xs font-bold tracking-widest text-slate-400 uppercase font-outfit">Verified Signatures</p>
                    <h3 class="text-5xl font-extrabold text-emerald-400 tracking-tight font-outfit">{attendance}</h3>
                </div>
                <div class="h-16 w-16 bg-gradient-to-br from-emerald-500/20 to-teal-500/20 border border-emerald-500/30 text-emerald-400 rounded-2xl flex items-center justify-center text-3xl group-hover:scale-110 transition-transform">
                    <i class="fa-solid fa-shield-check"></i>
                </div>
            </div>

            <div class="glass-panel p-8 rounded-3xl flex items-center justify-between md:col-span-2 lg:col-span-1 group hover:border-purple-500/50 transition-colors">
                <div class="space-y-2">
                    <p class="text-xs font-bold tracking-widest text-slate-400 uppercase font-outfit">Database Engine</p>
                    <h3 class="text-2xl font-extrabold text-white tracking-tight font-outfit mt-2">SQLite v3</h3>
                    <p class="text-xs text-slate-500 font-mono">Encrypted Local Cluster</p>
                </div>
                <div class="h-16 w-16 bg-gradient-to-br from-purple-500/20 to-fuchsia-500/20 border border-purple-500/30 text-purple-400 rounded-2xl flex items-center justify-center text-3xl group-hover:scale-110 transition-transform">
                    <i class="fa-solid fa-server"></i>
                </div>
            </div>
        </div>

        <div class="glass-panel rounded-3xl p-8 mt-8">
            <h3 class="text-sm font-bold text-white uppercase tracking-widest font-outfit mb-6">Administrative Workflows</h3>
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-6">
                <a href="/bulk" class="flex flex-col items-center justify-center p-8 bg-[#030712]/50 hover:bg-indigo-500/10 rounded-2xl border border-slate-700/50 hover:border-indigo-500/50 text-center group transition-all">
                    <i class="fa-solid fa-qrcode text-4xl text-indigo-400 mb-4 group-hover:scale-110 transition-transform"></i>
                    <span class="text-sm font-bold text-white font-outfit tracking-wide">Generate Matrix Data</span>
                </a>
                <a href="/download" class="flex flex-col items-center justify-center p-8 bg-[#030712]/50 hover:bg-emerald-500/10 rounded-2xl border border-slate-700/50 hover:border-emerald-500/50 text-center group transition-all">
                    <i class="fa-solid fa-file-excel text-4xl text-emerald-400 mb-4 group-hover:scale-110 transition-transform"></i>
                    <span class="text-sm font-bold text-white font-outfit tracking-wide">Export Relational Excel</span>
                </a>
                <a href="/download_qrs" class="flex flex-col items-center justify-center p-8 bg-[#030712]/50 hover:bg-amber-500/10 rounded-2xl border border-slate-700/50 hover:border-amber-500/50 text-center group transition-all">
                    <i class="fa-solid fa-box-archive text-4xl text-amber-400 mb-4 group-hover:scale-110 transition-transform"></i>
                    <span class="text-sm font-bold text-white font-outfit tracking-wide">Download Token Archive</span>
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

                # save in DB
                c.execute("""
                INSERT INTO students (name,email,token,start_time,end_time)
                VALUES (?,?,?,?,?)
                """, (name, email, token, start_time, end_time))

                # ✅ ATTENDANCE LINK
                qr_link = request.host_url + "mark/" + token

                # ✅ ONLINE QR IMAGE (IMPORTANT FIX)
                qr_image_url = "https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=" + qr_link

                # optional local save (for download zip later)
                img = qrcode.make(qr_link)
                file_path = f"static/qrs/{name.replace(' ','_')}.png"
                img.save(file_path)

                # send to emailjs
                js_students.append(f"{name},{email},{qr_link},{qr_image_url}")

                success += 1

            except Exception as e:
                print("ERROR:", e)

        conn.commit()
        conn.close()

        js_data = "\n".join(js_students)

        content = f"""
        <div class="max-w-3xl mx-auto glass-panel rounded-3xl p-12 text-center space-y-8">
            <div class="inline-flex p-6 bg-emerald-500/20 text-emerald-400 rounded-full border border-emerald-500/30 shadow-[0_0_30px_rgba(16,185,129,0.3)]">
                <i class="fa-solid fa-check-double text-5xl"></i>
            </div>
            <h2 class="text-3xl font-extrabold text-white tracking-tight font-outfit">Transmission Initiated</h2>
            <p class="text-slate-300 text-base max-w-md mx-auto leading-relaxed">
                Successfully encoded payloads for <span class="text-white font-bold px-2 py-1 bg-slate-800 rounded">{success}</span> entities. Automated background pipelines are dispatching credentials via API frameworks.
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

            <div class="pt-8 border-t border-slate-800/50">
                <a href='/dashboard' class="inline-flex items-center justify-center px-8 py-4 bg-slate-800 hover:bg-slate-700 text-white font-bold rounded-xl text-sm transition-all shadow-lg hover:-translate-y-0.5">
                    <i class="fa-solid fa-layer-group mr-2"></i> Return to Command Center
                </a>
            </div>
        </div>
        """
        return render_template_string(LAYOUT_TEMPLATE, content=content)

    content = """
    <div class="max-w-4xl mx-auto glass-panel rounded-3xl p-10 space-y-8">
        <div class="border-b border-slate-800/50 pb-6">
            <h2 class="text-3xl font-extrabold text-white tracking-tight font-outfit">Mass Deployment Engine</h2>
            <p class="text-sm text-slate-400 mt-2">Define temporal parameters and input structured entity array data.</p>
        </div>

        <form method='POST' class="space-y-8">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div class="space-y-2">
                    <label class='text-xs font-bold text-slate-400 uppercase tracking-widest font-outfit'>Initiation Timestamp</label>
                    <input type='datetime-local' name='start_time' class='w-full bg-[#030712]/50 border border-slate-700/50 rounded-xl px-5 py-3.5 text-sm text-white focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all' required>
                </div>
                <div class="space-y-2">
                    <label class='text-xs font-bold text-slate-400 uppercase tracking-widest font-outfit'>Termination Timestamp</label>
                    <input type='datetime-local' name='end_time' class='w-full bg-[#030712]/50 border border-slate-700/50 rounded-xl px-5 py-3.5 text-sm text-white focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all' required>
                </div>
            </div>

            <div class="space-y-2">
                <label class='text-xs font-bold text-slate-400 uppercase tracking-widest font-outfit'>Entity Array (Format: Name, Email)</label>
                <div class="relative">
                    <textarea name='data' class='w-full h-60 bg-[#030712]/50 border border-slate-700/50 rounded-xl p-5 text-sm text-white focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all font-mono leading-relaxed' placeholder="Alexander Pierce, alex@enterprise.com&#10;Sophia Chen, sophia@enterprise.com" required></textarea>
                    <div class="absolute bottom-4 right-4 bg-slate-800 px-2 py-1 rounded text-[10px] text-slate-400 font-mono border border-slate-700">CSV Mode</div>
                </div>
            </div>
            
            <button type='submit' class="w-full inline-flex items-center justify-center px-4 py-4 bg-gradient-to-r from-indigo-600 to-blue-700 hover:from-indigo-500 hover:to-blue-600 text-white font-bold rounded-xl text-base transition-all shadow-[0_0_20px_rgba(79,70,229,0.4)] hover:shadow-[0_0_30px_rgba(79,70,229,0.6)] hover:-translate-y-0.5">
                <i class="fa-solid fa-rocket mr-3"></i> Execute Cryptographic Generation Pipeline
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
    if not df_logs.empty:
        try:
            df_logs['date_only'] = df_logs['time'].apply(lambda x: x.split()[0] if x else '')
            attendance_counts = df_logs.groupby('date_only').size()

            plt.figure(figsize=(8, 4))
            plt.gcf().patch.set_facecolor('#111827')
            plt.gcf().patch.set_alpha(0.0) # Transparent background for the figure
            ax = plt.gca()
            ax.set_facecolor('#111827')
            ax.patch.set_alpha(0.0) # Transparent background for the axes
            
            # Premium bar chart styling
            bars = attendance_counts.plot(kind='bar', color='#4f46e5', width=0.5, ax=ax)
            
            ax.tick_params(colors='#94a3b8', labelsize=9)
            ax.spines['bottom'].set_color('#334155')
            ax.spines['left'].set_color('#334155')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.grid(axis='y', color='#334155', linestyle='--', alpha=0.3)
            
            plt.title("Chronological Verification Frequency", color='#f8fafc', fontsize=12, pad=15, weight='bold', fontname='sans-serif')
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            
            img_buf = io.BytesIO()
            plt.savefig(img_buf, format='png', transparent=True, bbox_inches='tight')
            img_buf.seek(0)
            import base64
            chart_url = "data:image/png;base64," + base64.b64encode(img_buf.getvalue()).decode('utf-8')
            plt.close()
        except Exception as e:
            print("Chart Engine Exception Log:", e)

    table_rows = ""
    if not df_logs.empty:
        for idx, row in df_logs.iterrows():
            table_rows += f"""
            <tr class="border-b border-slate-800/50 text-slate-300 text-sm hover:bg-indigo-500/5 transition-colors">
                <td class="px-6 py-4 font-mono text-slate-500 text-xs">{row['id']}</td>
                <td class="px-6 py-4 font-bold text-white">{row['name']}</td>
                <td class="px-6 py-4 font-mono text-indigo-300 text-xs">{row['time']}</td>
                <td class="px-6 py-4"><span class="px-3 py-1 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 rounded-full text-[10px] font-bold tracking-widest uppercase">Verified</span></td>
            </tr>
            """
    else:
        table_rows = """
        <tr>
            <td colspan="4" class="px-6 py-16 text-center text-sm text-slate-500 font-medium">No verified interactions logged in the relational database.</td>
        </tr>
        """

    content = f"""
    <div class="space-y-8 w-full max-w-7xl mx-auto">
        <div class="border-b border-slate-800/50 pb-6">
            <h2 class="text-3xl font-extrabold text-white tracking-tight font-outfit">Intelligence Analytics</h2>
            <p class="text-sm text-slate-400 mt-1">Cross-referencing configuration limits and real-time ingestion streams.</p>
        </div>

        <div class="grid grid-cols-1 xl:grid-cols-3 gap-6">
            <div class="xl:col-span-1 glass-panel rounded-3xl p-6 flex flex-col items-center justify-center border-t-4 border-t-indigo-500">
                <h3 class="text-xs font-bold text-slate-400 uppercase tracking-widest font-outfit mb-4 w-full text-left">Activity Plot</h3>
                {f'<img src="{chart_url}" class="w-full drop-shadow-2xl" />' if chart_url else '<div class="text-slate-600 text-xs text-center py-20 font-medium border border-dashed border-slate-800 rounded-xl w-full">Insufficient data points to plot timeline.</div>'}
            </div>
            
            <div class="xl:col-span-2 glass-panel rounded-3xl p-6 space-y-4 border-t-4 border-t-blue-500">
                <div class="flex justify-between items-center mb-4">
                    <h3 class="text-xs font-bold text-slate-400 uppercase tracking-widest font-outfit">Active Cryptographic Tokens</h3>
                    <span class="text-[10px] text-blue-400 bg-blue-500/10 px-2 py-1 rounded font-mono border border-blue-500/20">{len(df_config)} Nodes</span>
                </div>
                <div class="overflow-x-auto rounded-xl border border-slate-800/50 bg-[#030712]/50">
                    <table class="w-full text-left border-collapse">
                        <thead>
                            <tr class="bg-slate-900/80 border-b border-slate-800 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                                <th class="px-6 py-4">Index</th>
                                <th class="px-6 py-4">Identity Array</th>
                                <th class="px-6 py-4">Temporal Bounds (Start &rarr; End)</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-slate-800/50 text-sm text-slate-300">
                            {"".join([f'<tr class="hover:bg-blue-500/5"><td class="px-6 py-4 font-mono text-slate-600 text-xs">#{i+1}</td><td class="px-6 py-4 font-bold text-white">{r["name"]}</td><td class="px-6 py-4 font-mono text-slate-400 text-xs"><span class="text-emerald-400/80">{r["start_time"]}</span> &rarr; <span class="text-rose-400/80">{r["end_time"]}</span></td></tr>' for i, r in df_config.iterrows()]) if not df_config.empty else '<tr><td colspan="3" class="px-6 py-10 text-center text-slate-600 font-medium">Matrix unpopulated.</td></tr>'}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <div class="glass-panel rounded-3xl p-6 border-t-4 border-t-emerald-500">
            <h3 class="text-xs font-bold text-slate-400 uppercase tracking-widest font-outfit mb-6">Immutable Ledger Stream</h3>
            <div class="overflow-hidden border border-slate-800/50 rounded-xl bg-[#030712]/50 shadow-inner">
                <div class="max-h-[400px] overflow-y-auto custom-scrollbar">
                    <table class="w-full text-left border-collapse">
                        <thead class="sticky top-0 bg-slate-900/90 backdrop-blur-md border-b border-slate-800 text-[10px] font-bold text-slate-400 uppercase tracking-wider z-10 shadow-sm">
                            <tr>
                                <th class="px-6 py-4">Packet ID</th>
                                <th class="px-6 py-4">Verified Subject</th>
                                <th class="px-6 py-4">Network Timestamp</th>
                                <th class="px-6 py-4">State</th>
                            </tr>
                        </thead>
                        <tbody>
                            {table_rows}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        
        <style>
            /* Custom Scrollbar for Ledger */
            .custom-scrollbar::-webkit-scrollbar {{
                width: 6px;
            }}
            .custom-scrollbar::-webkit-scrollbar-track {{
                background: rgba(15, 23, 42, 0.5); 
            }}
            .custom-scrollbar::-webkit-scrollbar-thumb {{
                background: rgba(79, 70, 229, 0.3); 
                border-radius: 10px;
            }}
            .custom-scrollbar::-webkit-scrollbar-thumb:hover {{
                background: rgba(79, 70, 229, 0.6); 
            }}
        </style>
    </div>
    """
    return render_template_string(LAYOUT_TEMPLATE, content=content)

# ================= MARK ATTENDANCE (PUBLIC SCAN NODE) =================
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

    # Premium Public Facing Styles
    BASE_PUBLIC_STYLE = """
    font-family: 'Inter', system-ui, sans-serif; 
    text-align:center; 
    padding:100px 20px; 
    background-color:#030712; 
    background-image: radial-gradient(circle at 50% 0%, #1e1b4b 0%, transparent 70%);
    color:#f8fafc; 
    min-height:100vh; 
    box-sizing:border-box;
    display: flex;
    align-items: center;
    justify-content: center;
    """
    
    CARD_STYLE = """
    max-width:550px; 
    width: 100%;
    background: rgba(17, 24, 39, 0.7);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border:1px solid rgba(255,255,255,0.05); 
    padding:50px; 
    border-radius:32px; 
    box-shadow:0 25px 50px -12px rgba(0,0,0,0.5);
    """

    if not data:
        conn.close()
        return f"""
        <div style="{BASE_PUBLIC_STYLE}">
            <div style="{CARD_STYLE}">
                <div style="color:#ef4444; font-size:64px; margin-bottom:24px; text-shadow: 0 0 30px rgba(239,68,68,0.4);">✖</div>
                <h2 style="margin:0 0 12px 0; font-size:28px; font-weight:800; font-family: 'Arial', sans-serif;">Invalid Cryptographic Token</h2>
                <p style="color:#94a3b8; font-size:16px; line-height:1.6;">The AIMCS edge node failed to resolve this configuration sequence. The payload may be corrupted or manually altered.</p>
            </div>
        </div>
        """

    name = data[0]
    start_time = data[1]
    end_time = data[2]

    # Keeping your current timezone configuration (+4 hours over UTC)
    now = datetime.utcnow() + timedelta(hours=4)

    start_dt = datetime.strptime(start_time, "%Y-%m-%dT%H:%M")
    end_dt = datetime.strptime(end_time, "%Y-%m-%dT%H:%M")

    if now < start_dt:
        conn.close()
        return f"""
        <div style="{BASE_PUBLIC_STYLE}">
            <div style="{CARD_STYLE}">
                <div style="color:#ef4444; font-size:64px; margin-bottom:24px; text-shadow: 0 0 30px rgba(239,68,68,0.4);">🛑</div>
                <h2 style="margin:0 0 12px 0; font-size:28px; font-weight:800;">Validation Window Closed</h2>
                <p style="color:#94a3b8; font-size:16px; margin:0 0 30px 0; line-height:1.6;">This tracking sequence has not yet reached its initialized operational timeframe.</p>
                <div style="background-color:rgba(30, 41, 59, 0.5); padding:20px; border-radius:16px; font-family:monospace; font-size:14px; color:#60a5fa; border:1px solid rgba(59, 130, 246, 0.2);">
                    Awaiting Target Start: <br/><strong style="font-size:18px; color:#fff; display:block; margin-top:8px;">{start_dt.strftime('%Y-%m-%d %H:%M')}</strong>
                </div>
            </div>
        </div>
        """

    if now > end_dt:
        conn.close()
        return f"""
        <div style="{BASE_PUBLIC_STYLE}">
            <div style="{CARD_STYLE}">
                <div style="color:#f59e0b; font-size:64px; margin-bottom:24px; text-shadow: 0 0 30px rgba(245,158,11,0.4);">⚠️</div>
                <h2 style="margin:0 0 12px 0; font-size:28px; font-weight:800;">Link Terminated</h2>
                <p style="color:#94a3b8; font-size:16px; margin:0 0 30px 0; line-height:1.6;">The temporal processing window bounds for this entity have officially expired.</p>
                <div style="background-color:rgba(30, 41, 59, 0.5); padding:20px; border-radius:16px; font-family:monospace; font-size:14px; color:#f43f5e; border:1px solid rgba(244, 63, 94, 0.2);">
                    Terminated At: <br/><strong style="font-size:18px; color:#fff; display:block; margin-top:8px;">{end_dt.strftime('%Y-%m-%d %H:%M')}</strong>
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
                <div style="color:#3b82f6; font-size:64px; margin-bottom:24px; text-shadow: 0 0 30px rgba(59,130,246,0.4);">🔁</div>
                <h2 style="margin:0 0 12px 0; font-size:28px; font-weight:800;">Sequence Redundancy</h2>
                <p style="color:#94a3b8; font-size:16px; margin:0 0 24px 0; line-height:1.6;">Entity ingestion already processed securely within the logging database bounds.</p>
                <div style="border-top:1px solid rgba(255,255,255,0.1); padding-top:24px;">
                    <h3 style="color:#ffffff; margin:0; font-size:22px; font-weight:700;">{name}</h3>
                    <p style="color:#3b82f6; font-size:12px; text-transform:uppercase; letter-spacing:2px; margin-top:8px; font-weight:bold;">Status: Already Logged</p>
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
            <div style="color:#10b981; font-size:64px; margin-bottom:24px; text-shadow: 0 0 30px rgba(16,185,129,0.4);">✅</div>
            <h2 style="margin:0 0 12px 0; font-size:28px; font-weight:800; color:#10b981;">Ingestion Verified</h2>
            <p style="color:#94a3b8; font-size:16px; margin:0 0 30px 0; line-height:1.6;">Attendance successfully routed and locked inside the central database array.</p>
            <div style="background:rgba(16,185,129,0.1); border:1px solid rgba(16,185,129,0.2); padding:24px; border-radius:20px;">
                <h3 style="color:#ffffff; margin:0; font-size:24px; font-weight:800;">{name}</h3>
                <p style="color:#10b981; font-size:12px; font-family:monospace; margin-top:8px;">{time_str}</p>
            </div>
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
    app.run(host="0.0.0.0", port=5000)
