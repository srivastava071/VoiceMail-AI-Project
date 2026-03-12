import requests
import base64
from email.mime.text import MIMEText
from flask import session
import re

def clean_html(raw_html):

    # remove style blocks
    raw_html = re.sub(r'<style.*?>.*?</style>', '', raw_html, flags=re.DOTALL)

    # remove script blocks
    raw_html = re.sub(r'<script.*?>.*?</script>', '', raw_html, flags=re.DOTALL)

    # remove HTML tags
    raw_html = re.sub(r'<.*?>', '', raw_html)

    # remove extra whitespace
    raw_html = re.sub(r'\s+', ' ', raw_html)

    return raw_html.strip()


def get_latest_emails_with_body():
    token = session.get("token")

    headers = {
        "Authorization": f"Bearer {token['access_token']}"
    }

    response = requests.get(
        "https://gmail.googleapis.com/gmail/v1/users/me/messages?maxResults=2",
        headers=headers
)

    messages = response.json().get("messages", [])
    email_list = []

    for msg in messages:
        msg_id = msg["id"]

        msg_data = requests.get(
            f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}?format=full",
            headers=headers
        ).json()

        subject = ""
        body = ""

        # Get subject
        for item in msg_data["payload"]["headers"]:
            if item["name"] == "Subject":
                subject = item["value"]

        payload = msg_data["payload"]

        # Extract body safely
        if "parts" in payload:
            for part in payload["parts"]:
                mime = part.get("mimeType", "")
                data = part.get("body", {}).get("data")

                if data:
                    decoded = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")

                    if mime == "text/plain":
                        body = decoded
                        break
                    elif mime == "text/html" and not body:
                        body = clean_html(decoded)

        else:
            data = payload.get("body", {}).get("data")
            if data:
                decoded = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
                body = clean_html(decoded)

        # Clean and shorten
        body = body.strip().replace("\n", " ")
        summary = body[:300] if body else "No readable content found."

        email_list.append({
            "subject": subject if subject else "No Subject",
            "body": summary
        })

    return email_list


def send_email(to_email, subject, message_text):
    token = session.get("token")

    message = MIMEText(message_text)
    message['to'] = to_email
    message['subject'] = subject

    raw_message = base64.urlsafe_b64encode(
        message.as_bytes()
    ).decode()

    headers = {
        "Authorization": f"Bearer {token['access_token']}",
        "Content-Type": "application/json"
    }

    response = requests.post(
        "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
        headers=headers,
        json={"raw": raw_message}
    )

    return response.status_code in [200, 202, 204]