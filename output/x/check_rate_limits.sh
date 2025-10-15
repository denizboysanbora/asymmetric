#!/bin/bash
# Quick rate limit status checker
cd "$(dirname "$0")"
./venv/bin/python scripts/rate_limit_status.py "$@"

