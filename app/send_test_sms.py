from twilio.rest import Client
import os
from dotenv import load_dotenv

load_dotenv(override=True)


def send_sms(to, message):
    sid = os.getenv("TWILIO_ACCOUNT_SID")
    token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_FROM_NUMBER")

    # Strip any potential whitespace
    if sid:
        sid = sid.strip()
    if token:
        token = token.strip()
    if from_number:
        from_number = from_number.strip()

    print(f"DEBUG: SID='{sid}'")
    print(f"DEBUG: FROM='{from_number}'")

    client = Client(sid, token)

    try:
        msg = client.messages.create(from_=from_number, to=to, body=message)
        print("SMS SID:", msg.sid)
        print("Status:", msg.status)
    except Exception as e:
        print("Error:", str(e))


if __name__ == "__main__":
    send_sms("+919701555619", "Hello from Python SMS Test 🚀")
