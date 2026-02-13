from twilio.rest import Client
from django.conf import settings

client = Client(
    settings.TWILIO_ACCOUNT_SID,
    settings.TWILIO_AUTH_TOKEN
)

def send_sms(to, message):
    try:
        msg = client.messages.create(
            to=to,
            from_=settings.TWILIO_FROM_NUMBER,
            body=message
        )
        return {
            "success": True,
            "sid": msg.sid,
            "status": msg.status
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
