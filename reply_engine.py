import re


def generate_suggested_replies(message):

    if not message:
        return []

    text = message.lower()

    suggestions = []

    # Meeting related
    if any(word in text for word in ["meeting", "attend", "schedule"]):
        suggestions = [
            "Yes, I will attend.",
            "Sorry, I am not available.",
            "Can we reschedule?"
        ]

    # Thanks related
    elif "thank" in text:
        suggestions = [
            "You're welcome.",
            "Happy to help.",
            "Anytime!"
        ]

    # Urgent related
    elif "urgent" in text:
        suggestions = [
            "I will check and respond soon.",
            "On it.",
            "Let me handle this immediately."
        ]

    # Confirmation
    elif any(word in text for word in ["confirm", "ok", "okay"]):
        suggestions = [
            "Confirmed.",
            "Sounds good.",
            "Noted."
        ]

    # Default fallback
    else:
        suggestions = [
            "Thanks for the update.",
            "Got it.",
            "I will get back to you."
        ]

    return suggestions