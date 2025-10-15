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

BASE_DIR = Path(__file__).resolve().parent
ALPACA_DIR = Path(
    os.getenv("ALPACA_DIR", BASE_DIR / "alpaca" / "alpaca-mcp-server")
).resolve()

SCAN_SCRIPT = str(Path(os.getenv("TRADER_SCAN_SCRIPT", ALPACA_DIR / "scan.sh")).resolve())
EMAIL_SCRIPT = str(Path(os.getenv("TRADER_EMAIL_SCRIPT", ALPACA_DIR / "email.sh")).resolve())
TWEET_SCRIPT = str(Path(os.getenv("TRADER_TWEET_SCRIPT", ALPACA_DIR / "tweet.sh")).resolve())

DEFAULT_TIMEOUT = 30


def run_script(script_path, symbol):
    """Run helper scripts and centralize error handling."""
    try:
        result = subprocess.run(
            [script_path, symbol],
            capture_output=True,
            text=True,
            timeout=DEFAULT_TIMEOUT
        )
        return result, None
    except subprocess.TimeoutExpired:
        return None, "Command timed out"
    except Exception as exc:
        return None, str(exc)

def validate_symbol(symbol):
    """Validate symbol format (alphanumeric, 1-5 chars)."""
    if not re.match(r'^[A-Z0-9]{1,5}$', symbol.upper()):
        return False
    return True

def execute_scan(symbol):
    """Execute scan command."""
    result, error = run_script(SCAN_SCRIPT, symbol)
    if error:
        return {
            "success": False,
            "output": None,
            "error": error
        }

    if result.returncode == 0:
        return {
            "success": True,
            "output": result.stdout.strip(),
            "error": None
        }

    return {
        "success": False,
        "output": None,
        "error": result.stderr.strip() or "Scan failed"
    }

def execute_email(symbol):
    """Execute email command."""
    result, error = run_script(EMAIL_SCRIPT, symbol)
    if error:
        return {
            "success": False,
            "output": None,
            "error": error
        }

    if result.returncode == 0:
        return {
            "success": True,
            "output": f"✉️ Email sent for ${symbol}",
            "error": None
        }

    return {
        "success": False,
        "output": None,
        "error": result.stderr.strip() or "Email failed"
    }

def execute_tweet(symbol):
    """Execute tweet command."""
    result, error = run_script(TWEET_SCRIPT, symbol)
    if error:
        return {
            "success": False,
            "output": None,
            "error": error
        }

    output = result.stdout.strip()
    error_text = result.stderr.strip()

    if result.returncode == 0:
        return {
            "success": True,
            "output": output or f"🐦 Tweet sent for ${symbol}",
            "error": None
        }

    if "Rate limit reached" in error_text:
        return {
            "success": False,
            "output": None,
            "error": "🚫 Rate limit reached (17 tweets/24h)"
        }

    return {
        "success": False,
        "output": None,
        "error": error_text or "Tweet failed"
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
