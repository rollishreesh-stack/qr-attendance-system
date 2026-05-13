from flask import Flask, request, render_template_string
import csv
import datetime
import qrcode

app = Flask(__name__)

# Generate QR Code Automatically
url = "https://qr-attendance-system-th3j.onrender.com"

img = qrcode.make(url)
img.save("static/attendance_qr.png")

HTML = """
<h1>QR Attendance System</h1>

<form method="POST">

    <input type="text" name="name" placeholder="Enter Your Name" required>

    <button type="submit">Mark Attendance</button>

</form>
"""

@app.route("/", methods=["GET", "POST"])
def home():

    if request.method == "POST":

        name = request.form["name"]

        time = datetime.datetime.now()

        with open("attendance.csv", "a", newline="") as file:

            writer = csv.writer(file)

            writer.writerow([name, time])

        return f"<h2>Attendance Marked for {name}</h2>"

    return render_template_string(HTML)

@app.route("/data")
def data():
    with open("attendance.csv", "r") as f:
        return "<pre>" + f.read() + "</pre>"

@app.route("/check")
def check():
    with open("attendance.csv", "a") as f:
        f.write("TEST_ENTRY\n")
    return "written"

app.run(host="0.0.0.0", port=5001)
