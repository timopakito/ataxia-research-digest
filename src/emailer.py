import os

import requests

RESEND_URL = "https://api.resend.com/emails"


def send_digest(subject, html_body):
    api_key = os.environ["RESEND_API_KEY"]
    sender = os.environ["EMAIL_FROM"]
    recipients = [addr.strip() for addr in os.environ["EMAIL_TO"].split(",") if addr.strip()]

    resp = requests.post(
        RESEND_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "from": sender,
            "to": recipients,
            "subject": subject,
            "html": html_body,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()
