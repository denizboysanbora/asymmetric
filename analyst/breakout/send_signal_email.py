#!/usr/bin/env python3
"""
Simple email sending for breakout signals
"""

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_signal_email():
    """Send the breakout signals email"""
    
    # Email content
    subject = "Signal"
    body = """$INTC 37.01 +2.1% | ADR 5.6/5%+ | Range 8.3/15%+ | ATR 1.45/1.20 (0.83×)+ | V 141.2M/120.5M (1.2×)+ | RS 9.25/1.00+ | M 665.3/665.1 (10>20)+ | B 2.3/1.5%+ | Range Breakout
$PTON 7.50 +3.2% | ADR 6.8/5%+ | Range 12.1/15%+ | ATR 0.45/0.38 (0.84×)+ | V 15.3M/12.8M (1.2×)+ | RS 4.53/1.00+ | M 665.3/665.1 (10>20)+ | B 3.1/1.5%+ | Flag Breakout
$WDC 126.20 +1.8% | ADR 5.4/5%+ | Range 9.2/15%+ | ATR 2.15/1.85 (0.86×)+ | V 10.2M/8.9M (1.1×)+ | RS 11.31/1.00+ | M 665.3/665.1 (10>20)+ | B 2.8/1.5%+ | Range Breakout
$SEDG 37.02 +4.1% | ADR 8.0/5%+ | Range 11.5/15%+ | ATR 1.25/1.05 (0.84×)+ | V 3.5M/2.8M (1.3×)+ | RS 5.99/1.00+ | M 665.3/665.1 (10>20)+ | B 4.2/1.5%+ | Flag Breakout"""
    
    # Create message
    msg = MIMEMultipart()
    msg['From'] = "your-email@gmail.com"  # Replace with your email
    msg['To'] = "deniz@example.com"      # Replace with recipient
    msg['Subject'] = subject
    
    msg.attach(MIMEText(body, 'plain'))
    
    # Print the email content (for now, since SMTP setup needs credentials)
    print("📧 EMAIL CONTENT READY:")
    print("=" * 50)
    print(f"To: {msg['To']}")
    print(f"Subject: {msg['Subject']}")
    print("\nBody:")
    print(body)
    print("\n" + "=" * 50)
    print("✅ Email content generated successfully!")
    print("📝 To send via SMTP, configure your email credentials in the script.")
    
    return True

if __name__ == "__main__":
    send_signal_email()
