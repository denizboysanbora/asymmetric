# Investor Backend

This folder contains the backend logic for the Investor feature (formerly Trader).

## Contents

- `execute_command.py` - Thin wrapper that delegates to the shared investor backend
- `investor_backend/` - Reusable package for parsing/executing investor commands
- `tests/` - Unit tests covering command parsing and script execution edge cases

## Commands

The investor interface supports three commands:
- `scan SYMBOL` - Scan a stock or crypto symbol
- `email SYMBOL` - Send an email alert for a symbol
- `tweet SYMBOL` - Tweet about a symbol

## Dependencies

This backend relies on scripts from the `asymmetric/` folder:
- Scan scripts in `asymmetric/analyst/alpaca/alpaca-mcp-server/`
- Email scripts in `asymmetric/output/gmail/`
- Tweet scripts in `asymmetric/output/x/`

## Usage

The `execute_command.py` script is called from the Next.js API route at `/api/investor`.
It now delegates to `investor_backend.executor`, which centralizes validation and
execution logic for both the API and legacy Trader tooling.

## Setup

1. Use Python 3.10 or newer (the MCP SDK requires 3.10+). We recommend Homebrew's `python3.11`.
2. Create a virtual environment in the repo root: `python3.11 -m venv .venv`.
3. Install the trading dependencies: `pip install -r analyst/alpaca/alpaca-mcp-server/requirements.txt`.
4. Activate the environment whenever you run the investor scripts.

Environment variables:
- `INVESTOR_COMMAND_SCRIPT` - Path to execute_command.py (optional, auto-detected)
- `INVESTOR_PYTHON_BIN` - Path to Python interpreter (optional, defaults to system python3)
- `INVESTOR_COMMAND_TIMEOUT` - Override the subprocess timeout in seconds (optional)

### Development

Run the lightweight regression tests with:

```bash
python3 -m unittest discover -s analyst/tests
```
