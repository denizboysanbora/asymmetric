#!/usr/bin/env python3
"""
Test email functionality for Bob
This script simulates Bob running at 4 PM to test email sending
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import analyst modules
from output.gmail.send_email import send_email
import subprocess

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler('logs/test_email.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def test_email():
    """Test email functionality"""
    try:
        logger.info("🧪 Testing email functionality...")
        
        # Load environment variables
        load_dotenv('config/api_keys.env')
        
        # Test signal line (simulating a real signal)
        test_signal = "$AAPL $150.25 +2.45% | 65 RSI | 2.25x ATR | Z 1.85 | Breakout"
        
        logger.info(f"📧 Sending test email with signal: {test_signal}")
        
        # Send test email (need to provide recipient, subject, and body)
        # Get recipient from environment or use default
        recipient = os.getenv('GMAIL_RECIPIENT', 'deniz@bora.box')
        subject = "Breakout"  # Test subject
        body = test_signal
        
        send_email(recipient, subject, body)
        logger.info("✅ Test email sent successfully!")
        
        # Also send as tweet using same approach as analyst (subprocess call)
        logger.info(f"🐦 Sending test tweet with signal: {test_signal}")
        tweet_script = os.path.join(os.path.dirname(__file__), 'output', 'tweet', 'tweet_with_limit.py')
        result = subprocess.run(['python3', tweet_script, test_signal], 
                              capture_output=True, text=True, cwd=os.path.dirname(__file__))
        if result.returncode == 0:
            logger.info("✅ Test tweet sent successfully!")
            if result.stdout.strip():
                logger.info(f"   ↳ {result.stdout.strip()}")
        else:
            logger.error(f"❌ Tweet failed: {result.stderr}")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        raise

if __name__ == "__main__":
    test_email()
