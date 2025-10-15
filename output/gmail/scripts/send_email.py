#!/usr/bin/env python3
import base64
import os
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

BASE_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = BASE_DIR / 'config'
TOKEN_PATH = CONFIG_DIR / 'token.json'

SCOPES = ['https://www.googleapis.com/auth/gmail.send']


def create_message(to_email: str, subject: str, body: str) -> dict:
    message = MIMEText(body)
    message['to'] = to_email
    message['subject'] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {'raw': raw}


def send_email(to_email: str, subject: str, body: str) -> Optional[dict]:
    creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    service = build('gmail', 'v1', credentials=creds)
    message = create_message(to_email, subject, body)
    sent = service.users().messages().send(userId='me', body=message).execute()
    return sent

if __name__ == '__main__':
    # simple manual test
    import sys
    if len(sys.argv) < 4:
        print('Usage: send_email.py to subject body', flush=True)
        raise SystemExit(2)
    res = send_email(sys.argv[1], sys.argv[2], sys.argv[3])
    print(res)
