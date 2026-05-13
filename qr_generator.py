import qrcode

base_url = "https://your-app.onrender.com/mark?name="

students = ["John", "Alice", "Bob"]

for student in students:
    img = qrcode.make(base_url + student)
    img.save(f"{student}.png")
