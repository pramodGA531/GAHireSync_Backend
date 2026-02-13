import os
import django
from dotenv import load_dotenv

import sys
from pathlib import Path

# Set up Django environment
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "RTMAS_BACKEND.settings")
load_dotenv()
django.setup()

from app.whatsapp_service import send_whatsapp


def test_send():
    to = "+919701555619"
    message = "Hello from GA HireSync WhatsApp Service! 🚀"

    print(f"Attempting to send WhatsApp message to {to}...")
    result = send_whatsapp(to, message)

    if result.get("success"):
        print(f"Success! Message SID: {result.get('sid')}")
    else:
        print(f"Failed: {result.get('error')}")
        print(
            "\nNOTE: Ensure you have joined the Twilio WhatsApp Sandbox by sending 'join <your-sandbox-code>' to the sandbox number."
        )


if __name__ == "__main__":
    test_send()
