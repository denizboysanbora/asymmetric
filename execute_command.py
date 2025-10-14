#!/usr/bin/env python3
"""
Execute trading commands for Trader agent.
Usage: execute_command.py "scan AVGO"
Returns JSON: {"success": true, "output": "...", "error": null}
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
ALPACA_DIR = Path(
    os.getenv("ALPACA_DIR", BASE_DIR / "alpaca" / "alpaca-mcp-server")
).resolve()

SCAN_SCRIPT = str(Path(os.getenv("TRADER_SCAN_SCRIPT", ALPACA_DIR / "scan.sh")).resolve())
EMAIL_SCRIPT = str(Path(os.getenv("TRADER_EMAIL_SCRIPT", ALPACA_DIR / "email.sh")).resolve())
TWEET_SCRIPT = str(Path(os.getenv("TRADER_TWEET_SCRIPT", ALPACA_DIR / "tweet.sh")).resolve())

def validate_symbol(symbol):
    """Validate symbol format (alphanumeric, 1-5 chars)."""
    if not re.match(r'^[A-Z0-9]{1,5}$', symbol.upper()):
        return False
    return True

def execute_scan(symbol):
    """Execute scan command."""
    scan_script = SCAN_SCRIPT
    try:
        result = subprocess.run(
            [scan_script, symbol],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            return {
                "success": True,
                "output": result.stdout.strip(),
                "error": None
            }
        else:
            return {
                "success": False,
                "output": None,
                "error": result.stderr.strip() or "Scan failed"
            }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "output": None,
            "error": "Command timed out"
        }
    except Exception as e:
        return {
            "success": False,
            "output": None,
            "error": str(e)
        }

def execute_email(symbol):
    """Execute email command."""
    email_script = EMAIL_SCRIPT
    try:
        result = subprocess.run(
            [email_script, symbol],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            return {
                "success": True,
                "output": f"✉️ Email sent for ${symbol}",
                "error": None
            }
        else:
            return {
                "success": False,
                "output": None,
                "error": result.stderr.strip() or "Email failed"
            }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "output": None,
            "error": "Command timed out"
        }
    except Exception as e:
        return {
            "success": False,
            "output": None,
            "error": str(e)
        }

def execute_tweet(symbol):
    """Execute tweet command."""
    tweet_script = TWEET_SCRIPT
    try:
        result = subprocess.run(
            [tweet_script, symbol],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        output = result.stdout.strip()
        error = result.stderr.strip()
        
        if result.returncode == 0:
            return {
                "success": True,
                "output": output or f"🐦 Tweet sent for ${symbol}",
                "error": None
            }
        elif "Rate limit reached" in error:
            return {
                "success": False,
                "output": None,
                "error": "🚫 Rate limit reached (17 tweets/24h)"
            }
        else:
            return {
                "success": False,
                "output": None,
                "error": error or "Tweet failed"
            }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "output": None,
            "error": "Command timed out"
        }
    except Exception as e:
        return {
            "success": False,
            "output": None,
            "error": str(e)
        }

def parse_command(command_text):
    """Parse command text into (action, symbol)."""
    # Remove $ if present, split by whitespace
    parts = command_text.strip().replace('$', '').split()
    
    if len(parts) != 2:
        return None, None
    
    action = parts[0].lower()
    symbol = parts[1].upper()
    
    if action not in ['scan', 'email', 'tweet']:
        return None, None
    
    if not validate_symbol(symbol):
        return None, None
    
    return action, symbol

def main():
    if len(sys.argv) < 2:
        result = {
            "success": False,
            "output": None,
            "error": "Usage: execute_command.py \"scan AVGO\""
        }
        print(json.dumps(result))
        sys.exit(1)
    
    command_text = sys.argv[1]
    action, symbol = parse_command(command_text)
    
    if not action or not symbol:
        result = {
            "success": False,
            "output": None,
            "error": "Invalid command. Use: scan/email/tweet SYMBOL"
        }
        print(json.dumps(result))
        sys.exit(1)
    
    # Execute command
    if action == "scan":
        result = execute_scan(symbol)
    elif action == "email":
        result = execute_email(symbol)
    elif action == "tweet":
        result = execute_tweet(symbol)
    else:
        result = {
            "success": False,
            "output": None,
            "error": f"Unknown command: {action}"
        }
    
    print(json.dumps(result))
    sys.exit(0 if result["success"] else 1)

if __name__ == "__main__":
    main()

