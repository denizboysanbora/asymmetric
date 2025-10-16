#!/usr/bin/env python3
"""
Bob - GitHub Actions Market Analyst Worker
This script runs the same analysis as the local analyst but in GitHub Actions
"""

import os
import sys
import json
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import analyst modules
from input.alpaca.compute_spike_params_stocks import main as run_scanner
from output.database.log_signal import log_signal
from output.gmail.send_email import send_email
from output.tweet.post_text_oauth1 import post_tweet

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler('logs/bob.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    """Main Bob analyst function"""
    try:
        logger.info("🤖 Bob starting market analysis...")
        
        # Load environment variables
        load_dotenv('config/api_keys.env')
        
        # Check if we're in market hours (10 AM - 4 PM ET)
        if not is_market_hours():
            logger.info("⏰ Outside market hours, skipping analysis")
            return
        
        # Run the market scanner
        logger.info("🔍 Running market scanner...")
        scanner_output = run_scanner()
        
        if not scanner_output:
            logger.info("📊 No signals found")
            return
        
        # Parse the scanner output to find the best signal
        best_signal = parse_scanner_output(scanner_output)
        
        if best_signal:
            logger.info(f"🎯 Selected signal: {best_signal}")
            
            # Log to database
            try:
                log_signal(best_signal)
                logger.info("💾 Signal logged to database")
            except Exception as e:
                logger.error(f"❌ Database logging failed: {e}")
            
            # Send notifications
            try:
                send_notifications(best_signal)
                logger.info("📤 Notifications sent")
            except Exception as e:
                logger.error(f"❌ Notifications failed: {e}")
        else:
            logger.info("📊 No significant signals found")
            
    except Exception as e:
        logger.error(f"❌ Bob analyst error: {e}")
        raise

def is_market_hours():
    """Check if current time is within market hours (10 AM - 4 PM ET)"""
    now_et = datetime.now(timezone.utc).astimezone()
    hour = now_et.hour
    minute = now_et.minute
    
    # Market hours: 10 AM - 4 PM ET
    if hour < 10 or hour >= 16:
        return False
    
    # Only run every 30 minutes
    if minute not in [0, 30]:
        return False
    
    return True

def parse_scanner_output(output):
    """Parse scanner output to find the best signal"""
    if not output:
        return None
    
    # The scanner outputs signal lines, find the one with highest percentage change
    lines = output.strip().split('\n')
    signals = []
    
    for line in lines:
        if line.startswith('$') and '|' in line:
            try:
                # Parse signal line: $SYMBOL $PRICE ±X.XX% | ## RSI | X.XXx ATR | Z X.XX | Trend/Breakout
                parts = line.split('|')
                if len(parts) >= 5:
                    symbol_part = parts[0].strip()
                    change_part = parts[0].split()[-1]  # Get the percentage part
                    
                    if '%' in change_part:
                        change_pct = float(change_part.replace('%', ''))
                        signals.append({
                            'line': line,
                            'change_pct': abs(change_pct),
                            'original_change': change_pct
                        })
            except (ValueError, IndexError):
                continue
    
    if not signals:
        return None
    
    # Return the signal with highest absolute change
    best_signal = max(signals, key=lambda x: x['change_pct'])
    return best_signal['line']

def send_notifications(signal_line):
    """Send email and tweet notifications"""
    # Testing mode - disable Twitter notifications
    TESTING_MODE = os.getenv('BOB_TESTING_MODE', 'true').lower() == 'true'
    
    try:
        # Send email
        recipient = os.getenv('GMAIL_RECIPIENT', 'deniz@bora.box')
        subject = "Breakout" if "Breakout" in signal_line else "Trend"
        send_email(recipient, subject, signal_line)
        logger.info(f"📧 Email sent: {signal_line}")
    except Exception as e:
        logger.error(f"❌ Email failed: {e}")
    
    if TESTING_MODE:
        logger.info(f"🧪 TESTING MODE: Would send tweet: {signal_line}")
        logger.info("🧪 Twitter notifications disabled during testing")
    else:
        try:
            # Send tweet
            post_tweet(signal_line)
            logger.info(f"🐦 Tweet sent: {signal_line}")
        except Exception as e:
            logger.error(f"❌ Tweet failed: {e}")

if __name__ == "__main__":
    main()
