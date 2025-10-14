# Investor Backend

This folder contains the backend logic for the Investor feature (formerly Trader).

## Contents

- `execute_command.py` - Command executor for investor operations (scan/email/tweet)

## Commands

The investor interface supports three commands:
- `scan SYMBOL` - Scan a stock or crypto symbol
- `email SYMBOL` - Send an email alert for a symbol
- `tweet SYMBOL` - Tweet about a symbol

## Dependencies

This backend relies on scripts from the `asymmetric/` folder:
- Scan scripts in `asymmetric/alpaca/alpaca-mcp-server/`
- Email scripts in `asymmetric/gmail/`
- Tweet scripts in `asymmetric/x/`

## Usage

The `execute_command.py` script is called from the Next.js API route at `/api/investor`.

Environment variables:
- `INVESTOR_COMMAND_SCRIPT` - Path to execute_command.py (optional, auto-detected)
- `INVESTOR_PYTHON_BIN` - Path to Python interpreter (optional, defaults to system python3)
