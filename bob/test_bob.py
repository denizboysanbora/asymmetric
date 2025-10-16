#!/usr/bin/env python3
"""
Test script for Bob GitHub Actions setup
This script tests all the components without actually sending notifications
"""

import os
import sys
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s %(message)s'
)
logger = logging.getLogger(__name__)

def test_environment_variables():
    """Test that all required environment variables are set"""
    logger.info("🔍 Testing environment variables...")
    
    required_vars = [
        'ALPACA_API_KEY',
        'ALPACA_SECRET_KEY', 
        'SUPABASE_URL',
        'SUPABASE_SERVICE_KEY',
        'GMAIL_CLIENT_ID',
        'GMAIL_CLIENT_SECRET',
        'GMAIL_REFRESH_TOKEN',
        'TWITTER_API_KEY',
        'TWITTER_API_SECRET',
        'TWITTER_ACCESS_TOKEN',
        'TWITTER_ACCESS_SECRET'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"❌ Missing environment variables: {missing_vars}")
        return False
    else:
        logger.info("✅ All environment variables are set")
        return True

def test_imports():
    """Test that all required modules can be imported"""
    logger.info("🔍 Testing module imports...")
    
    try:
        from input.alpaca.compute_spike_params_stocks import main as run_scanner
        logger.info("✅ Alpaca scanner imported")
    except ImportError as e:
        logger.error(f"❌ Failed to import Alpaca scanner: {e}")
        return False
    
    try:
        from output.database.log_signal import log_signal
        logger.info("✅ Database module imported")
    except ImportError as e:
        logger.error(f"❌ Failed to import database module: {e}")
        return False
    
    try:
        from output.gmail.send_email import send_email
        logger.info("✅ Gmail module imported")
    except ImportError as e:
        logger.error(f"❌ Failed to import Gmail module: {e}")
        return False
    
    try:
        from output.tweet.post_text_oauth1 import post_tweet
        logger.info("✅ Twitter module imported")
    except ImportError as e:
        logger.error(f"❌ Failed to import Twitter module: {e}")
        return False
    
    return True

def test_market_hours():
    """Test market hours detection"""
    logger.info("🔍 Testing market hours detection...")
    
    from analyst import is_market_hours
    
    # Test current time
    current_status = is_market_hours()
    logger.info(f"Current market hours status: {current_status}")
    
    # Test timezone conversion
    now_utc = datetime.now(timezone.utc)
    now_et = now_utc.astimezone()
    logger.info(f"Current ET time: {now_et.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    
    return True

def test_signal_parsing():
    """Test signal parsing functionality"""
    logger.info("🔍 Testing signal parsing...")
    
    from analyst import parse_scanner_output
    
    # Test with sample output
    sample_output = """$PRAX $181.14 +228.45% | 54 RSI | 0.74x ATR | Z -0.27 | Trend
$AAPL $248.80 -0.55% | 54 RSI | 0.84x ATR | Z -0.48 | Trend"""
    
    result = parse_scanner_output(sample_output)
    if result:
        logger.info(f"✅ Signal parsing works: {result}")
        return True
    else:
        logger.error("❌ Signal parsing failed")
        return False

def main():
    """Run all tests"""
    logger.info("🤖 Bob test suite starting...")
    
    # Load environment variables
    load_dotenv('config/api_keys.env')
    
    tests = [
        ("Environment Variables", test_environment_variables),
        ("Module Imports", test_imports),
        ("Market Hours", test_market_hours),
        ("Signal Parsing", test_signal_parsing)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n--- Testing {test_name} ---")
        try:
            if test_func():
                passed += 1
                logger.info(f"✅ {test_name} passed")
            else:
                logger.error(f"❌ {test_name} failed")
        except Exception as e:
            logger.error(f"❌ {test_name} failed with error: {e}")
    
    logger.info(f"\n🎯 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! Bob is ready to run.")
        return True
    else:
        logger.error("❌ Some tests failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
