import qrcode

data_list = [
    "https://google.com",
    "https://youtube.com",
    "https://openai.com"
]

for i, data in enumerate(data_list):

    img = qrcode.make(data)

    filename = f"qr_{i+1}.png"

    img.save(filename)

    print(f"{filename} created!")