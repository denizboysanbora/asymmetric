#!/usr/bin/env python3
"""
Simple test email script that sends a test message without requiring network access for BTC data.
"""
import sys
from pathlib import Path

# Add Gmail venv to path
REPO_ROOT = Path(__file__).resolve().parents[1]
GMAIL_DIR = REPO_ROOT / "gmail"
sys.path.insert(0, str(GMAIL_DIR / "scripts"))
sys.path.insert(0, str(GMAIL_DIR / "venv" / "lib" / "python3.14" / "site-packages"))

from send_email import send_email


def main(to_email: str) -> int:
    subject = "Test Email - Asymmetric System"
    body = """Hello!

This is a test email from the Asymmetric trading system.

The system has been successfully reorganized into three main domains:
- analyst/ (market data & analysis)
- output/ (external communication)
- investor/ (trading strategies)

Email functionality is working correctly!

Best regards,
Asymmetric Trading System
"""
    
    try:
        result = send_email(to_email, subject, body)
        print(f"✅ Test email sent successfully!")
        print(f"   To: {to_email}")
        print(f"   Subject: {subject}")
        print(f"   Result: {result}")
        return 0
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: test_email.py you@example.com", flush=True)
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1]))



