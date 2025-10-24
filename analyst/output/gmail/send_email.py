#!/usr/bin/env python3
"""
Email sender for analyst signals
"""
import base64
import os
import re
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional, List

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

BASE_DIR = Path(__file__).resolve().parent
TOKEN_PATH = BASE_DIR / 'token.json'

SCOPES = ['https://www.googleapis.com/auth/gmail.send']

def _extract_signal_lines(text: str) -> List[str]:
    """Return all lines that match signal formats."""
    # Pattern for breakout: $SYMBOL $PRICE +X.XX% | ## RSI | X.XXx ATR | Signal Type
    # Updated to match various signal types (Flag Breakout, Range Breakout, Contraction, etc.)
    signal_patterns = [
        # Standard breakout format
        re.compile(
            r"^\$[A-Za-z0-9]{1,10}\s+\$[0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?\s+[+\-][0-9]+\.[0-9]{2}%\s+\|\s+[0-9]+\s+RSI\s+\|\s+[0-9]+\.[0-9]{2}x\s+ATR\s+\|\s+(Flag Breakout|Range Breakout|Contraction)$"
        ),
        # Extended format with more data
        re.compile(
            r"^\$[A-Za-z0-9]{1,10}\s+[0-9]+\.[0-9]{2}\s+[+\-][0-9]+\.[0-9]%\s+\|.*\|\s+(Flag Breakout|Range Breakout|Contraction|Breakout)$"
        ),
        # Simple format
        re.compile(
            r"^\$[A-Za-z0-9]{1,10}\s+[0-9]+\.[0-9]{2}\s+[+\-][0-9]+\.[0-9]%\s+\|.*\|\s+(Flag Breakout|Range Breakout|Contraction|Breakout)$"
        )
    ]

    signal_lines = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        # Check if line matches any signal pattern
        for pattern in signal_patterns:
            if pattern.match(line):
                signal_lines.append(line)
                break
    
    return signal_lines

def _normalize_body(subject: str, body: str) -> str:
    """Extract and return all valid signal lines with proper formatting."""
    signal_lines = _extract_signal_lines(body)
    
    if signal_lines:
        # Return all signal lines, each on its own line
        return "\n".join(signal_lines)
    
    # If no signals match patterns, return the original body
    # but ensure proper line breaks are preserved
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
    import sys
    if len(sys.argv) < 4:
        print('Usage: send_email.py to subject body', flush=True)
        raise SystemExit(2)
    res = send_email(sys.argv[1], sys.argv[2], sys.argv[3])
    print(res)
