import webbrowser
import time
from datetime import datetime
from flask import Flask, render_template, redirect, session, jsonify, request
from config import Config
from database import init_db
from oauth_config import init_oauth
from email_service import get_latest_emails_with_body, send_email
from speech import speak, take_voice_input, stop_speaking, set_language, get_language
import sqlite3
from reply_engine import generate_suggested_replies
from admin_logger import log_activity, log_api_usage, get_admin_stats

# ── App Setup

app = Flask(__name__)
app.config.from_object(Config)
app.config['TEMPLATES_AUTO_RELOAD'] = True

init_db()
google = init_oauth(app)


# ── Helper Functions

def require_login():
    if "user" not in session:
        return redirect("/")
    return None


# ── Routes

@app.route("/")
def home():
    if "user" in session:
        return redirect("/dashboard")
    return render_template("login.html")


@app.route("/login")
def login():
    if "onrender.com" in request.url_root:
        redirect_uri = request.url_root.replace("http://", "https://") + "auth"
    else:
        redirect_uri = request.url_root + "auth"
    return google.authorize_redirect(redirect_uri)


@app.route("/auth")
def auth():
    token = google.authorize_access_token()
    user_info = token["userinfo"]

    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute(
        "INSERT OR IGNORE INTO users (name, email, role) VALUES (?, ?, 'user')",
        (user_info["name"], user_info["email"])
    )
    conn.commit()
    c.execute("SELECT role FROM users WHERE email = ?", (user_info["email"],))
    row = c.fetchone()
    conn.close()

    role = row[0] if row else "user"

    session["user"]     = user_info["name"]
    session["email"]    = user_info["email"]
    session["token"]    = token
    session["welcomed"] = False
    session["language"] = "en-IN"
    session["theme"]    = "light"
    session["pin"]      = "2953"
    session["role"]     = role

    log_activity(user_info["email"], "login", f"User logged in: {user_info['name']}")
    set_language(session.get("language", "en-IN"))

    return redirect("/dashboard")


@app.route("/dashboard")
def dashboard():
    guard = require_login()
    if guard:
        return guard

    user_email = session.get("email", "")

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM activity_logs WHERE user_email=? AND action='emails_read'", (user_email,))
    emails_read = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM activity_logs WHERE user_email=? AND action='voice_command'", (user_email,))
    commands = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM activity_logs WHERE user_email=? AND action='login'", (user_email,))
    sessions = c.fetchone()[0]

    c.execute("""
        SELECT user_email, action, details, status, timestamp
        FROM activity_logs WHERE user_email=?
        ORDER BY timestamp DESC LIMIT 5
    """, (user_email,))
    recent_logs = c.fetchall()
    conn.close()

    stats = {"emails_read": emails_read, "commands": commands, "sessions": sessions}
    return render_template("dashboard.html", stats=stats, recent_logs=recent_logs)


@app.route("/profile", methods=["GET", "POST"])
def profile():
    guard = require_login()
    if guard:
        return guard

    if request.method == "POST":
        session["language"] = request.form.get("language", "en-IN")
        session["theme"]    = request.form.get("theme", "light")
        set_language(session["language"])   # ← sync to speech module
        return redirect("/profile")

    return render_template(
        "profile.html",
        language=session.get("language", "en-IN"),
        theme=session.get("theme", "light")
    )


@app.route("/logout")
def logout():
    log_activity(session.get("email", "unknown"), "logout", "User logged out")
    session.clear()
    return redirect("/")


@app.route("/register_rahul")
def register_rahul():
    from messaging_service import save_telegram_contact
    save_telegram_contact("rahul", "5530435086")
    return "Rahul Registered Successfully"


def verify_pin():
    speak("Please say your four digit security pin.")
    pin = take_voice_input()
    if not pin:
        speak("I could not hear your PIN.")
        return False
    if pin.strip() == session.get("pin"):
        speak("PIN verified.")
        return True
    else:
        speak("Incorrect PIN. Message cancelled.")
        return False


# ── Admin Routes

@app.route("/admin")
def admin_dashboard():
    guard = require_login()
    if guard:
        return guard

    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT role FROM users WHERE email=?", (session.get("email"),))
    row = c.fetchone()
    conn.close()

    role = row[0] if row else "user"

    if role != "admin":
        log_activity(session.get("email"), "admin_access_denied", "Attempted to access admin panel", status="error")
        return render_template("access_denied.html"), 403

    stats = get_admin_stats()
    return render_template("admin.html", stats=stats)


@app.route("/admin/make_admin", methods=["POST"])
def make_admin():
    guard = require_login()
    if guard:
        return guard
    if session.get("role") != "admin":
        return jsonify({"error": "Forbidden"}), 403
    email = request.json.get("email")
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("UPDATE users SET role='admin' WHERE email=?", (email,))
    conn.commit()
    conn.close()
    log_activity(session.get("email"), "make_admin", f"Granted admin role to {email}")
    return jsonify({"success": True})


@app.route("/admin/revoke_admin", methods=["POST"])
def revoke_admin():
    guard = require_login()
    if guard:
        return guard
    if session.get("role") != "admin":
        return jsonify({"error": "Forbidden"}), 403
    email = request.json.get("email")
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("UPDATE users SET role='user' WHERE email=?", (email,))
    conn.commit()
    conn.close()
    log_activity(session.get("email"), "revoke_admin", f"Revoked admin role from {email}")
    return jsonify({"success": True})


# @app.route("/admin/set_self_admin")
# def set_self_admin():
#     guard = require_login()
#     if guard: return guard
#     conn = sqlite3.connect("database.db")
#     c = conn.cursor()
#     c.execute("UPDATE users SET role='admin' WHERE email=?", (session.get("email"),))
#     conn.commit(); conn.close()
#     session["role"] = "admin"
#     log_activity(session.get("email"), "self_admin_grant", "User granted themselves admin role")
#     return redirect("/admin")


# ── Voice Route

@app.route("/voice", methods=["POST"])
def voice():
    guard = require_login()
    if guard:
        return jsonify({"error": "Unauthorized"}), 401

    stop_speaking()

    # Sync language from session every time
    lang = session.get("language", "en-IN")
    set_language(lang)
    is_hindi = (lang == "hi-IN")

    if not session.get("welcomed"):
        welcome_msg = f"नमस्ते {session['user']}, आप वापस आ गए।" if is_hindi else f"Welcome back, {session['user']}."
        speak(welcome_msg)
        session["welcomed"] = True
    
    browser_text = None
    if request.is_json:
        browser_text = request.json.get("command", "").strip()
    elif request.form:
        browser_text = request.form.get("command", "").strip()
 
    if browser_text:
        # Browser Web Speech API already transcribed — use it directly
        command = browser_text
        print(f"[Browser transcript received]: {command}")
    else:
        prompt = "कृपया अपना आदेश बोलें।" if is_hindi else "Please speak your command."
        speak(prompt)
        time.sleep(0.5)

        command = take_voice_input()

    if not command:
        log_activity(session.get("email"), "voice_command", "Could not understand voice input", status="error")
        err = "माफ करें, मैं समझ नहीं पाया। कृपया फिर बोलें।" if is_hindi else "Sorry, I could not understand. Please try again."
        speak(err)
        return jsonify({"command": "", "response": err})

    command_lower = command.lower()
    log_activity(session.get("email"), "voice_command", f"Command: {command}")

    # ── HELP
    if "help" in command_lower or "सहायता" in command_lower or "मदद" in command_lower:
        if is_hindi:
            help_text = ("आप कह सकते हैं: मेरे ईमेल पढ़ो, ईमेल भेजो, "
                         "अपठित ईमेल जांचो, समय क्या है, "
                         "आज की तारीख क्या है, जीमेल खोलो, या रुको।")
        else:
            help_text = ("You can say: Read my emails, Send email, "
                         "Check unread emails, What is the time, "
                         "What is today's date, Open Gmail, or Stop.")
        speak(help_text)
        return jsonify({"command": command, "response": help_text})

    # ── TIME
    elif "time" in command_lower or "समय" in command_lower or "टाइम" in command_lower:
        current_time = datetime.now().strftime("%I:%M %p")
        response = f"अभी का समय है {current_time}।" if is_hindi else f"The current time is {current_time}."
        speak(response)
        return jsonify({"command": command, "response": response})

    # ── DATE
    elif "date" in command_lower or "तारीख" in command_lower:
        today = datetime.now().strftime("%B %d, %Y")
        response = f"आज की तारीख है {today}।" if is_hindi else f"Today is {today}."
        speak(response)
        return jsonify({"command": command, "response": response})

    # ── CHECK UNREAD
    elif ("check" in command_lower and "unread" in command_lower) or "अपठित" in command_lower:
        emails = get_latest_emails_with_body()
        count = len(emails)
        response = f"आपके {count} नए ईमेल हैं।" if is_hindi else f"You have {count} recent email{'s' if count != 1 else ''}."
        speak(response)
        return jsonify({"command": command, "response": response})

    # ── OPEN GMAIL
    elif ("open" in command_lower and any(w in command_lower for w in ("email", "gmail", "mail"))) or "जीमेल" in command_lower:
        response = "जीमेल खोल रहा हूं।" if is_hindi else "Opening Gmail in your browser."
        speak(response)
        webbrowser.open("https://mail.google.com")
        return jsonify({"command": command, "response": response})

    # ── SEND MESSAGE (platform selection)
    elif ("send" in command_lower and "message" in command_lower) or "संदेश" in command_lower or "मैसेज" in command_lower:

        speak("कौन सा प्लेटफॉर्म? जीमेल, व्हाट्सएप, या टेलीग्राम?" if is_hindi else "Which platform? Gmail, WhatsApp, or Telegram?")
        platform = take_voice_input()

        if not platform:
            return jsonify({"command": command, "response": "Platform not understood."})

        platform = platform.lower()

        if "gmail" in platform:
            command_lower = "send email"

        elif "whatsapp" in platform or "व्हाट्सएप" in platform:
            speak("प्राप्तकर्ता का नाम बोलें।" if is_hindi else "Please say the recipient name.")
            recipient = take_voice_input()

            speak("अपना संदेश बोलें।" if is_hindi else "Please say your message.")
            message_text = take_voice_input()

            speak("क्या आप यह संदेश भेजना चाहते हैं?" if is_hindi else "Do you want to send this message?")
            confirmation = take_voice_input()

            if confirmation and ("yes" in confirmation.lower() or "हाँ" in confirmation or "हां" in confirmation):
                from messaging_service import send_whatsapp
                if not verify_pin():
                    return jsonify({"response": "Security verification failed."})
                success = send_whatsapp(recipient, message_text)
                log_api_usage(session.get("email"), "whatsapp_send")
                if success:
                    log_activity(session.get("email"), "whatsapp_sent", f"To: {recipient}")
                else:
                    log_activity(session.get("email"), "whatsapp_send_failed", f"To: {recipient}", status="error")
                response = ("व्हाट्सएप संदेश भेजा गया।" if is_hindi else "WhatsApp message sent successfully.") if success else ("व्हाट्सएप संदेश विफल।" if is_hindi else "Failed to send WhatsApp message.")
            else:
                response = "संदेश रद्द किया गया।" if is_hindi else "Message cancelled."

            speak(response)
            return jsonify({"command": command, "response": response})

        elif "telegram" in platform or "टेलीग्राम" in platform:
            speak("प्राप्तकर्ता का नाम बोलें।" if is_hindi else "Please say the recipient name.")
            recipient = take_voice_input()

            speak("अपना संदेश बोलें।" if is_hindi else "Please say your message.")
            message_text = take_voice_input()

            speak("क्या आप यह संदेश भेजना चाहते हैं?" if is_hindi else "Do you want to send this message?")
            confirmation = take_voice_input()

            if confirmation and ("yes" in confirmation.lower() or "हाँ" in confirmation or "हां" in confirmation):
                from messaging_service import send_telegram
                if not verify_pin():
                    return jsonify({"response": "Security verification failed."})
                success = send_telegram(recipient, message_text)
                log_api_usage(session.get("email"), "telegram_send")
                if success:
                    log_activity(session.get("email"), "telegram_sent", f"To: {recipient}")
                else:
                    log_activity(session.get("email"), "telegram_send_failed", f"To: {recipient}", status="error")
                response = ("टेलीग्राम संदेश भेजा गया।" if is_hindi else "Telegram message sent successfully.") if success else ("टेलीग्राम संदेश विफल।" if is_hindi else "Failed to send Telegram message.")
            else:
                response = "संदेश रद्द किया गया।" if is_hindi else "Message cancelled."

            speak(response)
            return jsonify({"command": command, "response": response})

        else:
            msg = "अज्ञात प्लेटफॉर्म।" if is_hindi else "Unknown platform selected."
            speak(msg)
            return jsonify({"command": command, "response": msg})

    # ── SEND EMAIL
    elif ("send" in command_lower and "email" in command_lower) or ("ईमेल" in command_lower and "भेजो" in command_lower):

        speak("प्राप्तकर्ता का ईमेल पता बोलें।" if is_hindi else "Please say the recipient's email address.")
        recipient = take_voice_input()

        if not recipient:
            return jsonify({"command": command, "response": "Recipient not understood."})

        recipient = (
            recipient.lower()
                     .replace(" at ", "@")
                     .replace(" dot ", ".")
                     .replace(" ", "")
        )

        speak("विषय बोलें।" if is_hindi else "Please say the subject.")
        subject = take_voice_input()

        if not subject:
            return jsonify({"command": command, "response": "Subject not understood."})

        speak("अपना संदेश बोलें।" if is_hindi else "Please say your message.")
        message_text = take_voice_input()

        if not message_text:
            return jsonify({"command": command, "response": "Message not understood."})

        confirm_prompt = f"{recipient} को भेजने के लिए हाँ बोलें।" if is_hindi else f"Ready to send to {recipient}. Say yes to confirm or no to cancel."
        speak(confirm_prompt)
        confirmation = take_voice_input()

        if confirmation and ("yes" in confirmation.lower() or "हाँ" in confirmation or "हां" in confirmation):
            if not verify_pin():
                return jsonify({"response": "Security verification failed."})
            success = send_email(recipient, subject, message_text)
            log_api_usage(session.get("email"), "gmail_send")
            if success:
                log_activity(session.get("email"), "email_sent", f"To: {recipient}, Subject: {subject}")
            else:
                log_activity(session.get("email"), "email_send_failed", f"To: {recipient}", status="error")
            if is_hindi:
                response = f"{recipient} को ईमेल भेजा गया।" if success else "ईमेल भेजने में त्रुटि।"
            else:
                response = f"Email sent successfully to {recipient}." if success else "There was an error sending the email."
        else:
            response = "ईमेल रद्द किया गया।" if is_hindi else "Email sending cancelled."

        speak(response)
        return jsonify({"command": command, "response": response})

    # ── READ EMAILS
    elif ("read" in command_lower and "email" in command_lower) or ("ईमेल" in command_lower and "पढ़" in command_lower):

        emails = get_latest_emails_with_body()
        log_api_usage(session.get("email"), "gmail_read")
        log_activity(session.get("email"), "emails_read", f"Read {len(emails)} emails")

        if not emails:
            response = "आपके कोई ईमेल नहीं हैं।" if is_hindi else "You have no emails."
            speak(response)
            return jsonify({"command": command, "response": response})

        count_msg = f"आपके {len(emails)} ईमेल हैं। पढ़ रहा हूं।" if is_hindi else f"You have {len(emails)} email{'s' if len(emails) != 1 else ''}. Reading now."
        speak(count_msg)

        response_data = []

        for i, email in enumerate(emails, 1):
            subject = email.get("subject") or "No subject"
            body    = email.get("body")    or "No content"

            try:
                from summarizer import extractive_summary
                summary = extractive_summary(body, max_sentences=2)
            except:
                summary = body[:150]

            speak(f"ईमेल {i}। विषय: {subject}। सारांश: {summary}" if is_hindi else f"Email {i}. Subject: {subject}. Summary: {summary}")

            response_data.append({
                "email_number": i,
                "subject":      subject,
                "summary":      summary,
            })

        return jsonify({"command": command, "emails": response_data})

    # ── SUGGEST REPLY
    elif "suggest reply" in command_lower or "सुझाव" in command_lower:

        speak("संदेश की सामग्री बोलें।" if is_hindi else "Please say the message content.")
        received_text = take_voice_input()

        suggestions = generate_suggested_replies(received_text)

        speak("यहाँ सुझाए गए उत्तर हैं।" if is_hindi else "Here are the suggested replies.")

        for i, suggestion in enumerate(suggestions, 1):
            speak(f"विकल्प {i}। {suggestion}" if is_hindi else f"Option {i}. {suggestion}")

        speak("विकल्प 1, 2, या 3 बोलें।" if is_hindi else "Say select option 1, 2, or 3.")
        choice = take_voice_input()

        if choice and "1" in choice:
            selected = suggestions[0]
        elif choice and "2" in choice:
            selected = suggestions[1]
        elif choice and "3" in choice:
            selected = suggestions[2]
        else:
            speak("अमान्य चयन।" if is_hindi else "Invalid selection.")
            return jsonify({"response": "Invalid selection."})

        speak("क्या आप यह उत्तर भेजना चाहते हैं?" if is_hindi else "Do you want to send this reply?")
        confirm = take_voice_input()

        if confirm and ("yes" in confirm.lower() or "हाँ" in confirm or "हां" in confirm):
            speak("उत्तर भेजा गया।" if is_hindi else "Reply sent successfully.")
            return jsonify({"response": selected})
        else:
            speak("उत्तर रद्द किया गया।" if is_hindi else "Reply cancelled.")
            return jsonify({"response": "Cancelled"})

    # ── STOP
    elif "stop" in command_lower or "रुको" in command_lower or "बंद" in command_lower:
        stop_speaking()
        return jsonify({"command": command, "response": "Stopped."})

    # ── UNKNOWN
    unknown = "माफ करें, यह आदेश नहीं समझा। सहायता के लिए मदद बोलें।" if is_hindi else "Sorry, I did not recognise that command. Say help to hear what I can do."
    speak(unknown)
    return jsonify({"command": command, "response": unknown})


# ── Stop Route

@app.route("/stop", methods=["POST"])
def stop():
    stop_speaking()
    return jsonify({"status": "stopped"})


@app.route("/show_contacts")
def show_contacts():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT * FROM telegram_contacts")
    data = c.fetchall()
    conn.close()
    return str(data)


@app.route("/register_whatsapp")
def register_whatsapp():
    from messaging_service import save_whatsapp_contact
    save_whatsapp_contact("himanshu", "9311415530")
    return "WhatsApp Contact Saved"


@app.route("/register_brother")
def register_brother():
    from messaging_service import save_whatsapp_contact
    save_whatsapp_contact("brother", "9560884631")
    return "Brother Registered Successfully"


@app.route("/unified_inbox")
def unified_inbox():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("""
        SELECT platform, sender, receiver, message, direction, timestamp
        FROM unified_messages
        ORDER BY timestamp DESC
    """)
    messages = c.fetchall()
    conn.close()
    return render_template("unified_inbox.html", messages=messages)


if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))