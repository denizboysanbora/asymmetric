"""
Investor backend utilities for executing trading actions from the command shell.

The package centralizes command parsing, script discovery, and execution so the
Next.js API route and legacy Trader tooling share the same logic.
"""

from .config import DEFAULT_TIMEOUT, ScriptPaths, load_script_paths
from .executor import Command, execute_action, main, parse_command

__all__ = [
    "Command",
    "DEFAULT_TIMEOUT",
    "ScriptPaths",
    "execute_action",
    "load_script_paths",
    "main",
    "parse_command",
]

