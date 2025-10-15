"""
Configuration helpers for the investor backend command executor.

These helpers determine where the scan, email, and tweet scripts live so both
the CLI wrapper and API layer stay in sync.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# Default timeout for subprocess calls (seconds)
DEFAULT_TIMEOUT = int(os.getenv("INVESTOR_COMMAND_TIMEOUT", "30"))


@dataclass(frozen=True)
class ScriptPaths:
    """Resolved filesystem locations for the helper shell scripts."""

    scan: Path
    email: Path
    tweet: Path


def repo_root() -> Path:
    """Return the repository root (one level above this package)."""
    return Path(__file__).resolve().parent.parent


def _normalize(path: Path) -> Path:
    """Expand user/home references and return an absolute path without requiring existence."""
    expanded = path.expanduser()
    try:
        return expanded.resolve()
    except FileNotFoundError:
        # When the path does not exist yet, fall back to the expanded absolute form.
        return expanded


def _resolve_env_path(env_var: str, default: Path) -> Path:
    """Resolve a script path from environment variables with a sensible default."""
    value = os.getenv(env_var)
    if value:
        candidate = Path(value.strip())
        if str(candidate).strip():
            return _normalize(candidate)
    return _normalize(default)


def load_script_paths() -> ScriptPaths:
    """Compute the canonical script locations for scan/email/tweet operations."""
    alpaca_default = repo_root() / "alpaca" / "alpaca-mcp-server"
    alpaca_dir = _resolve_env_path("ALPACA_DIR", alpaca_default)

    return ScriptPaths(
        scan=_resolve_env_path("TRADER_SCAN_SCRIPT", alpaca_dir / "scan.sh"),
        email=_resolve_env_path("TRADER_EMAIL_SCRIPT", alpaca_dir / "email.sh"),
        tweet=_resolve_env_path("TRADER_TWEET_SCRIPT", alpaca_dir / "tweet.sh"),
    )

