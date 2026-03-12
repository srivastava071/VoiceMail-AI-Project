# whatsapp_test.py

import os
from dotenv import load_dotenv
from twilio.rest import Client

# Load environment variables
load_dotenv()

account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")

if not account_sid or not auth_token:
    print("❌ Twilio credentials not found in .env file")
    exit()

client = Client(account_sid, auth_token)

try:
    message = client.messages.create(
        body="Milestone 3 WhatsApp test successful 🚀",
        from_="whatsapp:+14155238886",  # Twilio Sandbox Number
        to="whatsapp:+919311415530"   # 🔴 Replace with your number
    )

    print("✅ Message Sent Successfully")
    print("Message SID:", message.sid)

except Exception as e:
    print("❌ Error sending message:")
    print(e)