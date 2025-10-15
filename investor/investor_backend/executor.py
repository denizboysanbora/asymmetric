"""
Core execution logic for investor commands (scan/email/tweet).

This module exposes helpers that wrap the underlying shell scripts while
providing validation, consistent JSON responses, and reusable entry points for
CLI tools or API routes.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

from .config import DEFAULT_TIMEOUT, ScriptPaths, load_script_paths

VALID_ACTIONS = {"scan", "email", "tweet"}
SYMBOL_PATTERN = re.compile(r"^[A-Z0-9]{1,5}$")


@dataclass(frozen=True)
class Command:
    """Parsed representation of a user command."""

    action: str
    symbol: str


@dataclass
class ExecutionResult:
    """Structured result of executing a helper script."""

    action: str
    script_path: Path
    returncode: Optional[int]
    stdout: str
    stderr: str
    error: Optional[str] = None
    timed_out: bool = False

    @property
    def success(self) -> bool:
        return self.error is None and self.returncode == 0


def _normalize_symbol(symbol: str) -> str:
    """Strip common prefixes (like '$') and normalize case."""
    return symbol.strip().replace("$", "").upper()


def _is_valid_symbol(symbol: str) -> bool:
    """Return True when the symbol matches the allowed ticker pattern."""
    return bool(SYMBOL_PATTERN.fullmatch(symbol))


def _failure(message: str) -> dict[str, Optional[str]]:
    """Produce a standard failure payload."""
    return {"success": False, "output": None, "error": message}


def parse_command(command_text: str) -> Optional[Command]:
    """
    Parse the raw command string into a Command object.

    Accepts strings like "scan AVGO" or "tweet $TSLA". Returns None when the
    text does not match the expected <action> <symbol> shape.
    """
    if not command_text or not command_text.strip():
        return None

    parts = command_text.strip().split()
    if len(parts) != 2:
        return None

    action = parts[0].lower()
    if action not in VALID_ACTIONS:
        return None

    symbol = _normalize_symbol(parts[1])
    if not _is_valid_symbol(symbol):
        return None

    return Command(action=action, symbol=symbol)


def _script_for_action(action: str, paths: ScriptPaths) -> Path:
    """Retrieve the appropriate script path for the requested action."""
    if action not in VALID_ACTIONS:
        raise ValueError(f"Unsupported action: {action}")
    return getattr(paths, action)


def _invoke_script(
    action: str,
    script_path: Path,
    symbol: str,
    timeout: int = DEFAULT_TIMEOUT,
) -> ExecutionResult:
    """Execute the underlying helper script and capture stdout/stderr."""
    if not script_path.exists():
        return ExecutionResult(
            action, script_path, None, "", "", error=f"{action.title()} script not found: {script_path}"
        )

    if script_path.is_dir():
        return ExecutionResult(
            action,
            script_path,
            None,
            "",
            "",
            error=f"{action.title()} script path points to a directory: {script_path}",
        )

    try:
        completed = subprocess.run(
            [str(script_path), symbol],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return ExecutionResult(
            action=action,
            script_path=script_path,
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
    except subprocess.TimeoutExpired:
        return ExecutionResult(
            action,
            script_path,
            None,
            "",
            "",
            error=f"{action} command timed out after {timeout}s",
            timed_out=True,
        )
    except PermissionError:
        return ExecutionResult(
            action,
            script_path,
            None,
            "",
            "",
            error=f"{action.title()} script is not executable: {script_path}",
        )
    except FileNotFoundError:
        return ExecutionResult(
            action,
            script_path,
            None,
            "",
            "",
            error=f"{action.title()} script not found: {script_path}",
        )
    except Exception as exc:  # pragma: no cover - defensive guard
        return ExecutionResult(
            action,
            script_path,
            None,
            "",
            "",
            error=f"{action.title()} script error: {exc}",
        )


def _handle_scan(result: ExecutionResult) -> dict[str, Optional[str]]:
    if result.error:
        return _failure(result.error)
    if not result.success:
        message = result.stderr.strip() or "Scan failed"
        return _failure(message)
    return {"success": True, "output": result.stdout.strip(), "error": None}


def _handle_email(symbol: str, result: ExecutionResult) -> dict[str, Optional[str]]:
    if result.error:
        return _failure(result.error)
    if not result.success:
        message = result.stderr.strip() or "Email failed"
        return _failure(message)
    output_text = result.stdout.strip() or f"✉️ Email sent for ${symbol}"
    return {"success": True, "output": output_text, "error": None}


def _handle_tweet(symbol: str, result: ExecutionResult) -> dict[str, Optional[str]]:
    if result.error:
        return _failure(result.error)
    if not result.success:
        error_text = (result.stderr or "").strip()
        if "rate limit" in error_text.lower():
            return _failure("🚫 Rate limit reached (17 tweets/24h)")
        message = error_text or "Tweet failed"
        return _failure(message)
    output_text = result.stdout.strip() or f"🐦 Tweet sent for ${symbol}"
    return {"success": True, "output": output_text, "error": None}


def execute_action(
    action: str,
    symbol: str,
    *,
    paths: Optional[ScriptPaths] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, Optional[str]]:
    """
    Execute a trading action ('scan', 'email', 'tweet') for a ticker symbol.

    Returns a JSON-serializable dict with keys: success, output, error.
    """
    action = action.lower().strip()
    if action not in VALID_ACTIONS:
        return _failure(f"Unknown command: {action}")

    normalized_symbol = _normalize_symbol(symbol)
    if not _is_valid_symbol(normalized_symbol):
        return _failure("Invalid symbol. Use 1-5 alphanumeric characters.")

    script_paths = paths or load_script_paths()
    script_path = _script_for_action(action, script_paths)

    result = _invoke_script(action, script_path, normalized_symbol, timeout=timeout)

    if action == "scan":
        return _handle_scan(result)
    if action == "email":
        return _handle_email(normalized_symbol, result)
    if action == "tweet":
        return _handle_tweet(normalized_symbol, result)

    # This line should never be reached because action is validated above.
    return _failure(f"Unhandled command: {action}")  # pragma: no cover


def main(argv: Optional[Sequence[str]] = None) -> int:
    """
    CLI entrypoint for execute_command.py compatibility.

    Prints a JSON response and returns the process exit code.
    """
    if argv is None:
        argv = sys.argv[1:]

    if not argv:
        response = _failure('Usage: execute_command.py "scan AVGO"')
        print(json.dumps(response))
        return 1

    command_text = argv[0]
    command = parse_command(command_text)
    if not command:
        response = _failure("Invalid command. Use: scan/email/tweet SYMBOL")
        print(json.dumps(response))
        return 1

    result = execute_action(command.action, command.symbol)
    print(json.dumps(result))
    return 0 if result["success"] else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

