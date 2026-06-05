from flask import Flask, request, redirect, send_file
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
import sqlite3
from datetime import datetime, timedelta
import secrets
import qrcode
import os
import zipfile
import pandas as pd

app = Flask(__name__)
app.secret_key = "supersecretkey"

DB_NAME = "attendance.db"

# ================= DATABASE =================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

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

    conn.commit()
    conn.close()

init_db()

# ================= LOGIN =================
login_manager = LoginManager()
login_manager.init_app(app)

class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

# ================= STYLE =================
STYLE = """
<style>
body{
    margin:0;
    font-family:Arial;
    background:linear-gradient(135deg,#0f172a,#1e293b);
    color:white;
}

.header{
    background:#111827;
    padding:18px;
    text-align:center;
    font-size:24px;
    font-weight:bold;
}

.container{
    width:90%;
    max-width:1000px;
    margin:auto;
    margin-top:30px;
}

.card{
    background:white;
    color:black;
    padding:25px;
    border-radius:15px;
    margin-top:20px;
    box-shadow:0 5px 15px rgba(0,0,0,0.3);
}

button{
    width:100%;
    padding:12px;
    margin-top:10px;
    background:#2563eb;
    color:white;
    border:none;
    border-radius:10px;
    cursor:pointer;
}

textarea{
    width:100%;
    height:150px;
    padding:10px;
    border-radius:10px;
    margin-bottom:15px;
    box-sizing: border-box;
}

input[type="datetime-local"] {
    width: 100%;
    padding: 10px;
    margin-bottom: 15px;
    border-radius: 10px;
    border: 1px solid #ccc;
    box-sizing: border-box;
}

label {
    font-weight: bold;
    display: block;
    margin-bottom: 5px;
}

.stats{
    display:grid;
    grid-template-columns:repeat(auto-fit,minmax(200px,1fr));
    gap:15px;
}

.box{
    background:#2563eb;
    padding:20px;
    text-align:center;
    border-radius:12px;
}
</style>

<script src="https://cdn.jsdelivr.net/npm/@emailjs/browser@4/dist/email.min.js"></script>

<script>
(function(){
    emailjs.init("-oGl3hn1HEMpvxh2T");
})();
</script>
"""

# ================= HOME =================
@app.route("/")
def home():
    return f"""
    {STYLE}
    <div class='header'>🎓 QR Attendance System</div>

    <div class='container'>
        <div class='card'>
            <h2 style='text-align:center'>Bulk QR + Email System</h2>
            <a href='/dashboard'><button>Go Dashboard</button></a>
        </div>
    </div>
    """

# ================= DASHBOARD =================
@app.route("/dashboard")
def dashboard():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM students")
    students = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM attendance")
    attendance = c.fetchone()[0]

    conn.close()

    return f"""
    {STYLE}
    <div class='header'>📊 Dashboard</div>

    <div class='container'>

        <div class='stats'>
            <div class='box'>Students<br><h2>{students}</h2></div>
            <div class='box'>Attendance<br><h2>{attendance}</h2></div>
        </div>

        <div class='card'>
            <a href='/bulk'><button>➕ Bulk QR Generator</button></a>
            <a href='/download'><button>⬇️ Excel</button></a>
            <a href='/download_qrs'><button>📦 QR ZIP</button></a>
        </div>

    </div>
    """

# ================= BULK QR + EMAIL =================
@app.route("/bulk", methods=["GET","POST"])
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

        return f"""
        {STYLE}

        <div class='header'>✅ QR Generation Completed</div>

        <div class='container'>
            <div class='card'>
                <h2 style='text-align:center;color:green;'>
                    {success} QR Codes Generated
                </h2>

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

                <a href='/dashboard'>
                    <button>Back to Dashboard</button>
                </a>

            </div>
        </div>
        """

    return f"""
    {STYLE}

    <div class='header'>Bulk QR Generator</div>

    <div class='container'>
        <div class='card'>
            <form method='POST'>
                <label for='start_time'>Attendance Window Start Time:</label>
                <input type='datetime-local' name='start_time' id='start_time' required>

                <label for='end_time'>Attendance Window End Time:</label>
                <input type='datetime-local' name='end_time' id='end_time' required>

                <label for='data'>Student List (Format: Name,Email):</label>
                <textarea name='data' id='data' placeholder='John Doe, john@example.com&#10;Jane Doe, jane@example.com' required></textarea>
                
                <button type='submit'>Generate QR</button>
            </form>
        </div>
    </div>
    """

# ================= MARK ATTENDANCE =================
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
        return "Invalid QR"

    name = data[0]
    start_time = data[1]
    end_time = data[2]

    # Timezone calculation setup (+4 hours over UTC)
    now = datetime.utcnow() + timedelta(hours=4)

    start_dt = datetime.strptime(start_time, "%Y-%m-%dT%H:%M")
    end_dt = datetime.strptime(end_time, "%Y-%m-%dT%H:%M")

    if now < start_dt:
        conn.close()
        return f"""
        <h2 style='color:red;text-align:center;font-family:Arial;'>
        Attendance has not started yet
        <br><br>
        Start Time: {start_dt.strftime('%Y-%m-%d %H:%M')}
        </h2>
        """

    if now > end_dt:
        conn.close()
        return f"""
        <h2 style='color:red;text-align:center;font-family:Arial;'>
        Attendance Closed
        <br><br>
        End Time: {end_dt.strftime('%Y-%m-%d %H:%M')}
        </h2>
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
        <h2 style='text-align:center;font-family:Arial;color:orange;'>
        {name} already marked for today
        </h2>
        """

    time_str = now.strftime("%Y-%m-%d %H:%M:%S")

    c.execute("""
    INSERT INTO attendance(name,time)
    VALUES (?,?)
    """, (name,time_str))

    conn.commit()
    conn.close()

    return f"""
    <h1 style='text-align:center;color:green;font-family:Arial;'>
    Attendance Marked Successfully
    <br><br>
    {name}
    </h1>
    """

# ================= DOWNLOAD =================
@app.route("/download")
def download():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM attendance", conn)
    conn.close()

    file = "attendance.xlsx"
    df.to_excel(file,index=False)

    return send_file(file,as_attachment=True)

# ================= QR ZIP =================
@app.route("/download_qrs")
def zip_qr():
    z = zipfile.ZipFile("qrs.zip","w")

    if os.path.exists("static/qrs"):
        for f in os.listdir("static/qrs"):
            z.write("static/qrs/"+f)
    z.close()

    return send_file("qrs.zip",as_attachment=True)

# ================= RUN =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
