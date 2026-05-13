from flask import Flask, request
from datetime import datetime, timedelta

app = Flask(__name__)

# Store marked users (resets only if server restarts)
marked_users = set()

# Home page
@app.route("/", methods=["GET"])
def home():
    return """
    <h2>QR Attendance System</h2>
    <p>Scan QR to mark attendance</p>
    """

# QR Attendance Route
@app.route("/mark")
def mark():
    name = request.args.get("name")

    if not name:
        return "No name provided"

    # Prevent duplicate attendance
    if name in marked_users:
        return f"{name} already marked attendance!"

    # Georgia time (UTC +4)
    tbilisi_time = datetime.utcnow() + timedelta(hours=4)
    time_string = tbilisi_time.strftime("%Y-%m-%d %H:%M:%S")

    # Save attendance
    with open("attendance.csv", "a") as f:
        f.write(f"{name},{time_string}\n")

    marked_users.add(name)

    return f"Attendance marked for {name} at {time_string}"

# View attendance data
@app.route("/data")
def data():
    try:
        with open("attendance.csv", "r") as f:
            return "<pre>" + f.read() + "</pre>"
    except:
        return "No attendance data yet"

# Run app
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

