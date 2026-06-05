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
    <title>AIMCS | Advanced Attendance System</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <script src="https://cdn.jsdelivr.net/npm/@emailjs/browser@4/dist/email.min.js"></script>
    <script>
        (function(){
            emailjs.init("-oGl3hn1HEMpvxh2T");
        })();
    </script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        body { font-family: 'Inter', sans-serif; background-color: #0b0f19; }
    </style>
</head>
<body class="text-slate-200 min-h-screen flex">

    {% if current_user.is_authenticated %}
    <aside class="w-72 bg-[#111827] border-r border-slate-800 flex flex-col fixed h-full z-20 transition-all duration-300">
        <div class="p-6 border-b border-slate-800 flex items-center gap-3">
            <div class="bg-blue-600 p-2.5 rounded-xl text-white shadow-lg shadow-blue-500/30">
                <i class="fa-solid fa-graduation-cap text-xl"></i>
            </div>
            <div>
                <h1 class="text-lg font-bold text-white tracking-wide">AIMCS</h1>
                <p class="text-xs text-slate-400 font-medium">Attendance Management</p>
            </div>
        </div>
        
        <nav class="flex-1 p-4 space-y-1.5 mt-4">
            <a href="/" class="flex items-center gap-3.5 px-4 py-3 rounded-xl text-sm font-medium transition-all text-slate-400 hover:bg-slate-800/50 hover:text-white">
                <i class="fa-solid fa-house text-base w-5"></i> Home Gateway
            </a>
            <a href="/dashboard" class="flex items-center gap-3.5 px-4 py-3 rounded-xl text-sm font-medium transition-all text-slate-400 hover:bg-slate-800/50 hover:text-white">
                <i class="fa-solid fa-chart-pie text-base w-5"></i> Live Analytics Dashboard
            </a>
            <a href="/bulk" class="flex items-center gap-3.5 px-4 py-3 rounded-xl text-sm font-medium transition-all text-slate-400 hover:bg-slate-800/50 hover:text-white">
                <i class="fa-solid fa-qrcode text-base w-5"></i> Bulk QR Engine
            </a>
            <a href="/analysis" class="flex items-center gap-3.5 px-4 py-3 rounded-xl text-sm font-medium transition-all text-slate-400 hover:bg-slate-800/50 hover:text-white">
                <i class="fa-solid fa-chart-line text-base w-5"></i> Performance Report
            </a>
            <a href="/profile" class="flex items-center gap-3.5 px-4 py-3 rounded-xl text-sm font-medium transition-all text-slate-400 hover:bg-slate-800/50 hover:text-white">
                <i class="fa-solid fa-user-gear text-base w-5"></i> Security Settings
            </a>
            <a href="/logout" class="flex items-center gap-3.5 px-4 py-3 rounded-xl text-sm font-medium transition-all text-rose-400 hover:bg-rose-500/10 hover:text-rose-300">
                <i class="fa-solid fa-right-from-bracket text-base w-5"></i> Terminate Session
            </a>
        </nav>

        <div class="p-4 border-t border-slate-800">
            <div class="bg-slate-800/40 p-4 rounded-xl border border-slate-800 flex items-center gap-3">
                <div class="w-9 h-9 rounded-full bg-blue-500/20 text-blue-400 flex items-center justify-center font-bold text-sm">
                    {{ current_user.username[0].upper() }}
                </div>
                <div class="truncate">
                    <p class="text-xs font-semibold text-white truncate">{{ current_user.username }}</p>
                    <p class="text-[10px] text-slate-400 truncate">secure-session@active</p>
                </div>
            </div>
        </div>
    </aside>
    {% endif %}

    <main class="flex-1 {% if current_user.is_authenticated %}pl-72{% endif %} min-h-screen flex flex-col">
        <header class="h-20 bg-[#111827]/50 backdrop-blur-md border-b border-slate-800 flex items-center justify-between px-8 sticky top-0 z-10">
            <div class="flex items-center gap-2">
                <span class="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
                <p class="text-xs font-semibold tracking-wider text-slate-400 uppercase">AIMCS Core Ingestion Node: Operational</p>
            </div>
            <div class="text-sm font-medium text-slate-300">
                <i class="fa-regular fa-calendar-days mr-2 text-slate-400"></i> <span id="liveClock"></span>
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
            error_msg = "Invalid systemic credential mappings."

    content = f"""
    <div class="max-w-md w-full mx-auto my-auto bg-[#111827] border border-slate-800 rounded-2xl p-8 space-y-6 shadow-2xl">
        <div class="text-center space-y-2">
            <div class="inline-flex p-3 bg-blue-500/10 text-blue-500 rounded-xl mb-2">
                <i class="fa-solid fa-lock text-2xl"></i>
            </div>
            <h2 class="text-2xl font-bold text-white tracking-tight">AIMCS Access Verification</h2>
            <p class="text-xs text-slate-400">Provide root configuration deployment credentials.</p>
        </div>
        
        {f'<div class="p-3 bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs rounded-xl font-medium text-center">{error_msg}</div>' if error_msg else ''}

        <form method="POST" class="space-y-4">
            <div class="space-y-1.5">
                <label class="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Identified Username</label>
                <input type="text" name="username" class="w-full bg-slate-900 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-blue-500 transition-colors" placeholder="e.g. admin" required>
            </div>
            <div class="space-y-1.5">
                <label class="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Secure Access Token (Password)</label>
                <input type="password" name="password" class="w-full bg-slate-900 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-blue-500 transition-colors" placeholder="••••••••" required>
            </div>
            <button type="submit" class="w-full inline-flex items-center justify-center px-4 py-3 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-xl text-sm transition-all font-medium shadow-lg shadow-blue-500/10">
                Authenticate Session
            </button>
        </form>
        <div class="text-center text-[11px] text-slate-500 font-mono">
            Default Configuration Target: admin / admin123
        </div>
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
            status_msg = """<div class="p-3 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs rounded-xl font-medium text-center">Cryptographic passphrase mutation complete.</div>"""
        else:
            status_msg = """<div class="p-3 bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs rounded-xl font-medium text-center">Root verification mismatch. Verification aborted.</div>"""
        conn.close()

    content = f"""
    <div class="max-w-xl mx-auto bg-[#111827] border border-slate-800 rounded-2xl p-8 space-y-6">
        <div>
            <h2 class="text-xl font-bold text-white tracking-tight">Security & Encryption Administration</h2>
            <p class="text-xs text-slate-400 mt-1">Alter configuration system access layers dynamically.</p>
        </div>

        {status_msg}

        <form method="POST" class="space-y-4">
            <div class="space-y-1.5">
                <label class="text-xs font-semibold text-slate-400 uppercase tracking-wider">Current Passphrase</label>
                <input type="password" name="old_password" class="w-full bg-slate-900 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-blue-500 transition-colors" required>
            </div>
            <div class="space-y-1.5">
                <label class="text-xs font-semibold text-slate-400 uppercase tracking-wider">New Core Target Passphrase</label>
                <input type="password" name="new_password" class="w-full bg-slate-900 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-blue-500 transition-colors" required>
            </div>
            <button type="submit" class="w-full inline-flex items-center justify-center px-4 py-3 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-xl text-sm transition-all shadow-lg shadow-blue-500/10">
                Commit Cryptographic Changes
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
    <div class="max-w-3xl mx-auto mt-12 text-center space-y-6">
        <div class="inline-flex p-4 bg-blue-500/10 text-blue-500 rounded-3xl border border-blue-500/20 shadow-2xl shadow-blue-500/5 mb-2">
            <i class="fa-solid fa-shield-halved text-5xl"></i>
        </div>
        <h2 class="text-4xl font-extrabold text-white tracking-tight sm:text-5xl">
            AIMCS Core Infrastructure
        </h2>
        <p class="text-lg text-slate-400 max-w-xl mx-auto leading-relaxed">
            Instantaneous encrypted attendance matrix tracking, structural analytical mapping, automated notification dispatches, and granular user lifecycle auditing workflows.
        </p>
        <div class="pt-4">
            <a href="/dashboard" class="inline-flex items-center justify-center px-6 py-3.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-semibold rounded-xl transition-all shadow-lg shadow-blue-500/20 hover:scale-[1.02]">
                Access Control Dashboard <i class="fa-solid fa-arrow-right ml-2 text-sm"></i>
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
        <div>
            <h2 class="text-2xl font-bold text-white tracking-tight">System Overview</h2>
            <p class="text-sm text-slate-400">AIMCS Environment real-time telemetry analytics calculations.</p>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <div class="bg-[#111827] border border-slate-800/80 p-6 rounded-2xl flex items-center justify-between">
                <div class="space-y-1">
                    <p class="text-sm font-medium text-slate-400">Total Registered Students</p>
                    <h3 class="text-3xl font-bold text-white tracking-tight">{students}</h3>
                </div>
                <div class="h-12 w-12 bg-blue-500/10 border border-blue-500/20 text-blue-500 rounded-xl flex items-center justify-center text-xl">
                    <i class="fa-solid fa-users"></i>
                </div>
            </div>

            <div class="bg-[#111827] border border-slate-800/80 p-6 rounded-2xl flex items-center justify-between">
                <div class="space-y-1">
                    <p class="text-sm font-medium text-slate-400">Total Valid Checks Logged</p>
                    <h3 class="text-3xl font-bold text-emerald-400 tracking-tight">{attendance}</h3>
                </div>
                <div class="h-12 w-12 bg-emerald-500/10 border border-emerald-500/20 text-emerald-500 rounded-xl flex items-center justify-center text-xl">
                    <i class="fa-solid fa-circle-check"></i>
                </div>
            </div>

            <div class="bg-[#111827] border border-slate-800/80 p-6 rounded-2xl flex items-center justify-between md:col-span-2 lg:col-span-1">
                <div class="space-y-1">
                    <p class="text-sm font-medium text-slate-400">Database Framework</p>
                    <h3 class="text-lg font-bold text-white tracking-tight">SQLite3 Infrastructure</h3>
                </div>
                <div class="h-12 w-12 bg-purple-500/10 border border-purple-500/20 text-purple-400 rounded-xl flex items-center justify-center text-xl">
                    <i class="fa-solid fa-database"></i>
                </div>
            </div>
        </div>

        <div class="bg-[#111827] border border-slate-800/80 rounded-2xl p-6">
            <h3 class="text-base font-semibold text-white mb-4">Operational Administrative Control Console</h3>
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <a href="/bulk" class="flex flex-col items-center justify-center p-5 bg-slate-800/30 hover:bg-slate-800/60 rounded-xl border border-slate-800 text-center group transition-all">
                    <i class="fa-solid fa-plus-circle text-2xl text-blue-500 mb-2 group-hover:scale-110 transition-transform"></i>
                    <span class="text-sm font-semibold text-white">Bulk QR Generator</span>
                </a>
                <a href="/download" class="flex flex-col items-center justify-center p-5 bg-slate-800/30 hover:bg-slate-800/60 rounded-xl border border-slate-800 text-center group transition-all">
                    <i class="fa-solid fa-file-excel text-2xl text-emerald-500 mb-2 group-hover:scale-110 transition-transform"></i>
                    <span class="text-sm font-semibold text-white">Export Excel Sheet</span>
                </a>
                <a href="/download_qrs" class="flex flex-col items-center justify-center p-5 bg-slate-800/30 hover:bg-slate-800/60 rounded-xl border border-slate-800 text-center group transition-all">
                    <i class="fa-solid fa-file-zipper text-2xl text-amber-500 mb-2 group-hover:scale-110 transition-transform"></i>
                    <span class="text-sm font-semibold text-white">Download QR Archive</span>
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

                # send to emailjs (Removed qr_link text mapping payload)
                js_students.append(f"{name},{email},{qr_image_url}")

                success += 1

            except Exception as e:
                print("ERROR:", e)

        conn.commit()
        conn.close()

        js_data = "\n".join(js_students)

        content = f"""
        <div class="max-w-2xl mx-auto bg-[#111827] border border-slate-800 rounded-2xl p-8 text-center space-y-6">
            <div class="inline-flex p-4 bg-emerald-500/10 text-emerald-500 rounded-full border border-emerald-500/20 shadow-xl shadow-emerald-500/5">
                <i class="fa-solid fa-circle-check text-4xl"></i>
            </div>
            <h2 class="text-2xl font-bold text-white tracking-tight">AIMCS QR Generation Initiated</h2>
            <p class="text-slate-400 text-sm max-w-sm mx-auto">
                Successfully configured dynamic targets for <span class="text-white font-semibold">{success}</span> recipients. Pipelines are processing background tasks via browser API contexts.
            </p>

            <script>
            const students = `{js_data}`.trim().split('\\n');

            students.forEach(s => {{
                let p = s.split(",");
                if (p.length < 3) return;
                let name = p[0];
                let email = p[1];
                let qr_image = p[2];

                emailjs.send(
                    "service_iuneir8",
                    "template_uyhe7xo",
                    {{
                        name: name,
                        email: email,
                        qr_image: qr_image
                    }}
                );
            }});
            </script>

            <div class="pt-4 border-t border-slate-800">
                <a href='/dashboard' class="inline-flex w-full items-center justify-center px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-white font-semibold rounded-xl text-sm transition-all">
                    Return to Management Dashboard
                </a>
            </div>
        </div>
        """
        return render_template_string(LAYOUT_TEMPLATE, content=content)

    content = """
    <div class="max-w-3xl mx-auto bg-[#111827] border border-slate-800 rounded-2xl p-8 space-y-6">
        <div>
            <h2 class="text-xl font-bold text-white tracking-tight">Bulk Dispatch Architecture</h2>
            <p class="text-xs text-slate-400 mt-1">Configure valid verification temporal windows and recipient structural array datasets mappings.</p>
        </div>

        <form method='POST' class="space-y-5">
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div class="space-y-1.5">
                    <label class='text-xs font-semibold text-slate-400 uppercase tracking-wider'>Window Start Runtime</label>
                    <input type='datetime-local' name='start_time' class='w-full bg-slate-900 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-blue-500 transition-colors' required>
                </div>
                <div class="space-y-1.5">
                    <label class='text-xs font-semibold text-slate-400 uppercase tracking-wider'>Window Termination Runtime</label>
                    <input type='datetime-local' name='end_time' class='w-full bg-slate-900 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-blue-500 transition-colors' required>
                </div>
            </div>

            <div class="space-y-1.5">
                <label class='text-xs font-semibold text-slate-400 uppercase tracking-wider'>Student Structured Array Dataset (Format: Name,Email)</label>
                <textarea name='data' class='w-full h-44 bg-slate-900 border border-slate-800 rounded-xl p-4 text-sm text-white focus:outline-none focus:border-blue-500 transition-colors font-mono' placeholder="Jane Doe, jane@example.com&#10;John Smith, john@example.com" required></textarea>
            </div>
            
            <button type='submit' class="w-full inline-flex items-center justify-center px-4 py-3 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-xl text-sm transition-all shadow-lg shadow-blue-500/10">
                Execute Encryption & Launch Notification Pipelines
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

            plt.figure(figsize=(7, 3.2))
            plt.gcf().patch.set_facecolor('#111827')
            ax = plt.gca()
            ax.set_facecolor('#111827')
            
            attendance_counts.plot(kind='bar', color='#2563eb', edgecolor='#3b82f6', width=0.4, ax=ax)
            
            ax.tick_params(colors='white', labelsize=8)
            ax.spines['bottom'].set_color('#334155')
            ax.spines['left'].set_color('#334155')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.grid(axis='y', color='#334155', linestyle='--', alpha=0.5)
            
            plt.title("Chronological Logs Mapping", color='white', fontsize=10, pad=10, weight='bold')
            plt.tight_layout()
            
            img_buf = io.BytesIO()
            plt.savefig(img_buf, format='png', facecolor=plt.gcf().get_facecolor(), bbox_inches='tight')
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
            <tr class="border-b border-slate-800/60 text-slate-300 text-xs hover:bg-slate-800/20 transition-colors">
                <td class="px-6 py-3.5 font-medium text-white">{row['id']}</td>
                <td class="px-6 py-3.5 font-semibold text-blue-400">{row['name']}</td>
                <td class="px-6 py-3.5 font-mono text-slate-400">{row['time']}</td>
                <td class="px-6 py-3.5"><span class="px-2 py-0.5 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-md text-[10px] font-bold">VERIFIED</span></td>
            </tr>
            """
    else:
        table_rows = """
        <tr>
            <td colspan="4" class="px-6 py-12 text-center text-sm text-slate-500 font-medium">No system check-ins captured within the relational ledger array.</td>
        </tr>
        """

    content = f"""
    <div class="space-y-8">
        <div>
            <h2 class="text-2xl font-bold text-white tracking-tight">Analytical Metric Performance Reports</h2>
            <p class="text-sm text-slate-400">AIMCS statistical metrics computations framework.</p>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div class="lg:col-span-1 bg-[#111827] border border-slate-800 rounded-2xl p-5 flex flex-col justify-center items-center">
                {f'<img src="{chart_url}" class="rounded-xl w-full" />' if chart_url else '<div class="text-slate-500 text-xs text-center py-12 font-medium">Insufficient timeline allocation instances to draw live plot configurations.</div>'}
            </div>
            
            <div class="lg:col-span-2 bg-[#111827] border border-slate-800 rounded-2xl p-6 space-y-4">
                <h3 class="text-sm font-semibold text-white uppercase tracking-wider">Active Token Allocations Table</h3>
                <div class="overflow-x-auto border border-slate-800 rounded-xl bg-slate-900/50">
                    <table class="w-full text-left border-collapse">
                        <thead>
                            <tr class="bg-slate-800/40 border-b border-slate-800 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                                <th class="px-6 py-3">Mapping Instance</th>
                                <th class="px-6 py-3">Identified Subject Target</th>
                                <th class="px-6 py-3">Configured Temporal Allocation Bounds</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-slate-800/60 text-xs text-slate-300">
                            {"".join([f'<tr class="hover:bg-slate-800/10"><td class="px-6 py-3 font-mono text-slate-500">#{i+1}</td><td class="px-6 py-3 font-medium text-white">{r["name"]}</td><td class="px-6 py-3 font-mono text-slate-400 text-[11px]">{r["start_time"]} &rarr; {r["end_time"]}</td></tr>' for i, r in df_config.iterrows()]) if not df_config.empty else '<tr><td colspan="3" class="px-6 py-6 text-center text-slate-500">Empty config structural dataset elements.</td></tr>'}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <div class="bg-[#111827] border border-slate-800 rounded-2xl p-6">
            <h3 class="text-sm font-semibold text-white uppercase tracking-wider mb-4">Real-Time Ingestion Logs Stream</h3>
            <div class="overflow-hidden border border-slate-800 rounded-xl bg-slate-900/50">
                <div class="max-h-96 overflow-y-auto">
                    <table class="w-full text-left border-collapse">
                        <thead class="sticky top-0 bg-[#161f30] border-b border-slate-800 text-[10px] font-bold text-slate-400 uppercase tracking-wider z-10">
                            <tr>
                                <th class="px-6 py-3">Ingestion Index</th>
                                <th class="px-6 py-3">Validated Entity Target</th>
                                <th class="px-6 py-3">System Timestamp Record</th>
                                <th class="px-6 py-3">Cryptographic State</th>
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

    if not data:
        conn.close()
        return """
        <div style="font-family:Arial,sans-serif; text-align:center; padding:50px; background:#0b0f19; min-height:100vh; color:white; box-sizing:border-box;">
            <h2 style="color:#ef4444; margin-top:100px;">Invalid Cryptographic Token</h2>
            <p style="color:#94a3b8;">The AIMCS scanning node returned an unmapped configuration sequence.</p>
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
        <div style="font-family:Arial,sans-serif; text-align:center; padding:100px 20px; background-color:#0b0f19; color:#f8fafc; min-height:100vh; box-sizing:border-box;">
            <div style="max-width:500px; margin:0 auto; background-color:#111827; border:1px solid #1e293b; padding:40px; border-radius:20px; box-shadow:0 10px 25px rgba(0,0,0,0.3)">
                <div style="color:#ef4444; font-size:48px; margin-bottom:20px;">🛑</div>
                <h2 style="margin:0 0 10px 0; font-size:24px; font-weight:700;">Validation Window Closed</h2>
                <p style="color:#94a3b8; font-size:14px; margin:0 0 24px 0;">This attendance tracking session has not reached initialized start verification timelines.</p>
                <div style="background-color:#1e293b; padding:15px; border-radius:12px; font-family:monospace; font-size:13px; color:#3b82f6;">
                    Target Runtime Start: {start_dt.strftime('%Y-%m-%d %H:%M')}
                </div>
            </div>
        </div>
        """

    if now > end_dt:
        conn.close()
        return f"""
        <div style="font-family:Arial,sans-serif; text-align:center; padding:100px 20px; background-color:#0b0f19; color:#f8fafc; min-height:100vh; box-sizing:border-box;">
            <div style="max-width:500px; margin:0 auto; background-color:#111827; border:1px solid #1e293b; padding:40px; border-radius:20px; box-shadow:0 10px 25px rgba(0,0,0,0.3)">
                <div style="color:#ef4444; font-size:48px; margin-bottom:20px;">⚠️</div>
                <h2 style="margin:0 0 10px 0; font-size:24px; font-weight:700;">Validation Link Terminated</h2>
                <p style="color:#94a3b8; font-size:14px; margin:0 0 24px 0;">The temporal processing window bounds for this entity target has fully closed.</p>
                <div style="background-color:#1e293b; padding:15px; border-radius:12px; font-family:monospace; font-size:13px; color:#f43f5e;">
                    Terminated Runtime Bound: {end_dt.strftime('%Y-%m-%d %H:%M')}
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
        <div style="font-family:Arial,sans-serif; text-align:center; padding:100px 20px; background-color:#0b0f19; color:#f8fafc; min-height:100vh; box-sizing:border-box;">
            <div style="max-width:500px; margin:0 auto; background-color:#111827; border:1px solid #1e293b; padding:40px; border-radius:20px; box-shadow:0 10px 25px rgba(0,0,0,0.3)">
                <div style="color:#f59e0b; font-size:48px; margin-bottom:20px;">🔁</div>
                <h2 style="margin:0 0 10px 0; font-size:24px; font-weight:700;">Sequence Redundancy</h2>
                <p style="color:#94a3b8; font-size:14px; margin:0 0 10px 0;">Entity ingestion already processed securely within the logging database bounds.</p>
                <h3 style="color:#f59e0b; margin:0; font-size:18px;">{name} Already Logged</h3>
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
    <div style="font-family:Arial,sans-serif; text-align:center; padding:100px 20px; background-color:#0b0f19; color:#f8fafc; min-height:100vh; box-sizing:border-box;">
        <div style="max-width:500px; margin:0 auto; background-color:#111827; border:1px solid #1e293b; padding:40px; border-radius:20px; box-shadow:0 10px 25px rgba(0,0,0,0.3)">
            <div style="color:#10b981; font-size:48px; margin-bottom:20px;">✅</div>
            <h2 style="margin:0 0 10px 0; font-size:24px; font-weight:700; color:#10b981;">Ingestion Verified</h2>
            <p style="color:#94a3b8; font-size:14px; margin:0 0 20px 0;">Attendance successfully saved inside the secure database array.</p>
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
    app.run(host="0.0.0.0", port=5000)
