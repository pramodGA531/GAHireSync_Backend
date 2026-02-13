from twilio.rest import Client
from django.conf import settings


def send_whatsapp(to, message):
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

    # Twilio Sandbox number is usually +14155238886
    # In production, replace with your verified WhatsApp number
    from_number = getattr(settings, "TWILIO_WHATSAPP_NUMBER", "+14155238886")

    try:
        msg = client.messages.create(
            from_=f"whatsapp:{from_number}", to=f"whatsapp:{to}", body=message
        )
        return {"success": True, "sid": msg.sid, "status": msg.status}
    except Exception as e:
        return {"success": False, "error": str(e)}
