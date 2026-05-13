from flask import Flask, request
from datetime import datetime, timedelta

app = Flask(__name__)

# Home page (attendance form)
@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        name = request.form["name"]

        # ✅ FIXED TIME (Georgia = UTC +4)
        tbilisi_time = datetime.utcnow() + timedelta(hours=4)
        time_string = tbilisi_time.strftime("%Y-%m-%d %H:%M:%S")

        # Save attendance
        with open("attendance.csv", "a") as f:
            f.write(f"{name},{time_string}\n")

        return f"Attendance marked for {name} at {time_string}"

    return """
    <h2>QR Attendance System</h2>
    <form method="POST">
        <input name="name" placeholder="Enter Name" required>
        <button type="submit">Mark Attendance</button>
    </form>
    """

# View attendance data
@app.route("/data")
def data():
    try:
        with open("attendance.csv", "r") as f:
            return "<pre>" + f.read() + "</pre>"
    except:
        return "No attendance data yet"

@app.route("/mark")
def mark():
    name = request.args.get("name")

    if not name:
        return "No name provided"

    tbilisi_time = datetime.utcnow() + timedelta(hours=4)
    time_string = tbilisi_time.strftime("%Y-%m-%d %H:%M:%S")

    with open("attendance.csv", "a") as f:
        f.write(f"{name},{time_string}\n")

    return f"Attendance marked for {name} at {time_string}"

# Run app
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

