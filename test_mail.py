import smtplib
from email.message import EmailMessage

SENDER_EMAIL = "SRolli@gmail.com"
SENDER_PASSWORD = "kqyyxhotchppqdwj"

receiver_email = "YOUR_OTHER_EMAIL@gmail.com"

msg = EmailMessage()

msg["Subject"] = "SMTP Test"
msg["From"] = SENDER_EMAIL
msg["To"] = receiver_email

msg.set_content("Test email successful")

try:

    print("CONNECTING")

    server = smtplib.SMTP_SSL(
        "smtp.gmail.com",
        465
    )

    print("LOGGING IN")

    server.login(
        SENDER_EMAIL,
        SENDER_PASSWORD
    )

    print("SENDING")

    server.send_message(msg)

    print("SUCCESS EMAIL SENT")

    server.quit()

except Exception as e:

    print("FAILED")
    print(type(e))
    print(e)
