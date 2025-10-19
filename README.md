# Asymmetric Trading System

This project contains automated trading bots for breakout analysis and paper trading.

## Quick Start

The setup scripts and requirements have been moved to the `analyst/` folder:

- **Setup environment**: `cd analyst && ./scripts/bootstrap_env.sh`
- **Install cron jobs**: `cd analyst && ./scripts/install_cron.sh --apply`
- **Requirements**: `analyst/requirements.txt`

## Structure

- `analyst/` - Breakout analysis and MCP integration
- `investor/` - Paper trading bot
- `analyst/scripts/` - Setup and automation scripts
- `analyst/requirements.txt` - Python dependencies

For detailed setup instructions, see `analyst/docs/README.md`.
