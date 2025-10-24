#!/usr/bin/env python3
"""Simple email test script"""
import sys
import os
from email.mime.text import MIMEText
import base64

# Try importing Gmail API dependencies
try:
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    
    GMAIL_AVAILABLE = True
except ImportError as e:
    GMAIL_AVAILABLE = False
    GMAIL_ERROR = str(e)

def test_email_creation():
    """Test creating an email message"""
    print("Testing email creation...")
    
    test_body = """$INTC 37.01 +2.1% | ADR 5.6/5%+ | Range Breakout
$PTON 7.50 +3.2% | ADR 6.8/5%+ | Flag Breakout"""
    
    message = MIMEText(test_body)
    message['to'] = "deniz@bora.box"
    message['subject'] = "Test Signal"
    
    print("\n✅ Email message created successfully!")
    print("\nMessage details:")
    print(f"To: {message['to']}")
    print(f"Subject: {message['subject']}")
    print(f"\nBody:\n{test_body}")
    
    if GMAIL_AVAILABLE:
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        print(f"\n✅ Message encoded for Gmail API")
        return True
    else:
        print("\n⚠️  Gmail API not available for actual sending")
        return False

def test_credentials():
    """Test if Gmail credentials exist"""
    token_path = os.path.join(os.path.dirname(__file__), 'output/gmail/token.json')
    creds_path = os.path.join(os.path.dirname(__file__), 'output/gmail/credentials.json')
    
    print("\nChecking credentials...")
    if os.path.exists(creds_path):
        print(f"✅ credentials.json found at: {creds_path}")
    else:
        print(f"❌ credentials.json NOT found at: {creds_path}")
        
    if os.path.exists(token_path):
        print(f"✅ token.json found at: {token_path}")
    else:
        print(f"⚠️  token.json NOT found at: {token_path} (run gmail_auth.py first)")

if __name__ == '__main__':
    print("=" * 60)
    print("EMAIL FUNCTIONALITY TEST")
    print("=" * 60)
    print()
    
    test_email_creation()
    print()
    test_credentials()
    
    print("\n" + "=" * 60)
    if GMAIL_AVAILABLE:
        print("✅ Email functionality is ready!")
        print("\nNext step: Authenticate with Gmail")
        print("Run: python3 output/gmail/scripts/gmail_auth.py")
    else:
        print("⚠️  Need to install dependencies first")
        print(f"Error: {GMAIL_ERROR if 'GMAIL_ERROR' in globals() else 'Gmail API not available'}")
        print("\nInstall Python 3.10+ and run:")
        print("  ./scripts/bootstrap_env.sh")
    print("=" * 60)

