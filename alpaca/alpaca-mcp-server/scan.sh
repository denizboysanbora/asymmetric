#!/bin/bash
# Wrapper script for scan.py
cd "$(dirname "$0")"
./venv/bin/python3 scan.py "$@"

