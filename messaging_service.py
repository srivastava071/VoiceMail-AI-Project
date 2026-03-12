import os
import requests
import sqlite3
from dotenv import load_dotenv
from twilio.rest import Client

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")


# ============================================================
# 🔹 UNIFIED MESSAGE LOGGER
# ============================================================

def save_unified_message(platform, sender, receiver, message, direction):

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("""
        INSERT INTO unified_messages (platform, sender, receiver, message, direction)
        VALUES (?, ?, ?, ?, ?)
    """, (platform, sender, receiver, message, direction))

    conn.commit()
    conn.close()


# ============================================================
# 🔹 TELEGRAM SECTION
# ============================================================

def get_chat_id_from_db(name):

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("SELECT chat_id FROM telegram_contacts WHERE name=?", (name.lower(),))
    result = c.fetchone()

    conn.close()

    return result[0] if result else None


def save_telegram_contact(name, chat_id):

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("""
        INSERT OR REPLACE INTO telegram_contacts (name, chat_id)
        VALUES (?, ?)
    """, (name.lower(), chat_id))

    conn.commit()
    conn.close()


# 🔹 Telegram Simulation Mode
def send_telegram_simulation(receiver, message):

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram credentials missing.")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": f"[SIMULATION] To {receiver}: {message}"
    }

    try:
        response = requests.post(url, data=data)

        if response.status_code == 200:
            save_unified_message("telegram", "voice_assistant", receiver, message, "outgoing")
            return True
        return False

    except Exception as e:
        print("Telegram Simulation Error:", e)
        return False


# 🔹 Telegram Real Mode
def send_telegram(receiver, message):

    if not TELEGRAM_BOT_TOKEN:
        print("Telegram token missing.")
        return False

    chat_id = get_chat_id_from_db(receiver)

    if not chat_id:
        print("Contact not found in DB. Using simulation mode.")
        return send_telegram_simulation(receiver, message)

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    data = {
        "chat_id": chat_id,
        "text": message
    }

    try:
        response = requests.post(url, data=data)

        if response.status_code == 200:
            save_unified_message("telegram", "voice_assistant", receiver, message, "outgoing")
            return True
        return False

    except Exception as e:
        print("Telegram Real Mode Error:", e)
        return False


# ============================================================
# 🔹 WHATSAPP SECTION (TWILIO)
# ============================================================

def save_whatsapp_contact(name, phone):

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("""
        INSERT OR REPLACE INTO whatsapp_contacts (name, phone)
        VALUES (?, ?)
    """, (name.lower(), phone))

    conn.commit()
    conn.close()


def get_whatsapp_phone(name):

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("SELECT phone FROM whatsapp_contacts WHERE name=?", (name.lower(),))
    result = c.fetchone()

    conn.close()

    return result[0] if result else None


def send_whatsapp(receiver, message):

    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        print("Twilio credentials missing.")
        return False

    phone = get_whatsapp_phone(receiver)

    if not phone:
        print("WhatsApp contact not found in DB.")
        return False

    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

    try:
        msg = client.messages.create(
            body=message,
            from_="whatsapp:+14155238886",  # Twilio Sandbox Number
            to=f"whatsapp:+91{phone}"
        )

        print("WhatsApp Message SID:", msg.sid)

        save_unified_message("whatsapp", "voice_assistant", receiver, message, "outgoing")

        return True

    except Exception as e:
        print("WhatsApp Error:", e)
        return False