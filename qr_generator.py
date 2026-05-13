import qrcode

base_url = "https://your-app.onrender.com/mark?name="

students = ["John", "Alice", "Bob"]

for s in students:
    img = qrcode.make(base_url + s)
    img.save(f"{s}.png")
