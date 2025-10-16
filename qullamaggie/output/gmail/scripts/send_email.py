#!/usr/bin/env python3
import base64
import os
from email.mime.text import MIMEText
import re
from pathlib import Path
from typing import Optional

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

BASE_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = BASE_DIR / 'config'
TOKEN_PATH = CONFIG_DIR / 'token.json'

SCOPES = ['https://www.googleapis.com/auth/gmail.send']


def _extract_signal_line(text: str) -> str | None:
    """Return the first line that matches the strict signal format.

    Expected: "$SYMBOL $PRICE +X.XX% | X.XXx ATR | Z X.XX | Breakout"
    - SYMBOL: letters/numbers up to ~10 chars (e.g., BTC, NVDA)
    - PRICE: thousands with commas, optional cents
    - Percent: signed with 2 decimals
    - ATR multiple: 2 decimals
    - Z value: signed optional, 2 decimals
    """
    strict_pattern = re.compile(
        r"^\$[A-Za-z0-9]{1,10}\s+\$[0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?\s+[+\-][0-9]+\.[0-9]{2}%\s+\|\s+[0-9]+\.[0-9]{2}x\s+ATR\s+\|\s+Z\s+[+\-]?[0-9]+\.[0-9]{2}\s+\|\s+Breakout$"
    )

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if strict_pattern.match(line):
            return line
    # Fallback: any line ending with "| Breakout" that begins with a symbol and price
    fallback = re.compile(r"^\$[A-Za-z0-9]{1,10}\\s+\$.*\|\s*Breakout$")
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if fallback.match(line):
            return line
    return None


def _normalize_body(subject: str, body: str) -> str:
    """If a valid signal line exists in the body, return ONLY that line.
    This enforces the format and removes any additional text.
    Applies regardless of subject, but especially for "Signal" emails.
    """
    signal_line = _extract_signal_line(body)
    if signal_line is not None:
        return signal_line
    return body


def create_message(to_email: str, subject: str, body: str) -> dict:
    body_to_send = _normalize_body(subject, body)
    message = MIMEText(body_to_send)
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
