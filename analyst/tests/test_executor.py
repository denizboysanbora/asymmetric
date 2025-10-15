import stat
import tempfile
import textwrap
import unittest
from pathlib import Path

import sys
from pathlib import Path

# Ensure `investor/` is importable after repo reorg
REPO_ROOT = Path(__file__).resolve().parents[2]
INVESTOR_DIR = REPO_ROOT / "investor"
if str(INVESTOR_DIR) not in sys.path:
    sys.path.insert(0, str(INVESTOR_DIR))

from investor_backend.config import ScriptPaths
from investor_backend.executor import execute_action, parse_command


def _make_script(directory: Path, name: str, body: str) -> Path:
    """Create an executable script within a temporary directory."""
    path = directory / name
    script_body = textwrap.dedent(body).lstrip("\n")
    path.write_text(script_body)
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return path


class ExecutorTests(unittest.TestCase):
    def test_parse_command_valid(self):
        command = parse_command("scan AAPL")
        self.assertIsNotNone(command)
        self.assertEqual(command.action, "scan")
        self.assertEqual(command.symbol, "AAPL")

    def test_parse_command_rejects_invalid(self):
        self.assertIsNone(parse_command("scan"))
        self.assertIsNone(parse_command("scan TOO_LONG"))
        self.assertIsNone(parse_command("unknown AAPL"))

    def test_execute_scan_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            scan_script = _make_script(
                tmp_dir,
                "scan.sh",
                """
                #!/usr/bin/env python3
                import sys
                print(f"Signal for {sys.argv[1]}")
                """,
            )
            paths = ScriptPaths(scan=scan_script, email=scan_script, tweet=scan_script)
            result = execute_action("scan", "AAPL", paths=paths)
            self.assertTrue(result["success"])
            self.assertEqual(result["output"], "Signal for AAPL")

    def test_execute_email_uses_default_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            scan_script = _make_script(
                tmp_dir, "scan.sh", "#!/usr/bin/env python3\nimport sys\nprint('unused')\n"
            )
            email_script = _make_script(
                tmp_dir,
                "email.sh",
                "#!/usr/bin/env python3\nimport sys\n# intentionally quiet\n",
            )
            tweet_script = _make_script(
                tmp_dir,
                "tweet.sh",
                "#!/usr/bin/env python3\nimport sys\nprint('tweet ok')\n",
            )
            paths = ScriptPaths(scan=scan_script, email=email_script, tweet=tweet_script)
            result = execute_action("email", "aapl", paths=paths)
            self.assertTrue(result["success"])
            self.assertEqual(result["output"], "✉️ Email sent for $AAPL")

    def test_execute_tweet_rate_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            scan_script = _make_script(
                tmp_dir, "scan.sh", "#!/usr/bin/env python3\nimport sys\nprint('ok')\n"
            )
            email_script = _make_script(
                tmp_dir, "email.sh", "#!/usr/bin/env python3\nimport sys\nprint('ok')\n"
            )
            tweet_script = _make_script(
                tmp_dir,
                "tweet.sh",
                """
                #!/usr/bin/env python3
                import sys
                sys.stderr.write("Rate limit reached: 17/17\\n")
                sys.exit(1)
                """,
            )
            paths = ScriptPaths(scan=scan_script, email=email_script, tweet=tweet_script)
            result = execute_action("tweet", "TSLA", paths=paths)
            self.assertFalse(result["success"])
            self.assertEqual(result["error"], "🚫 Rate limit reached (17 tweets/24h)")

    def test_execute_missing_script(self):
        missing = Path("/not/a/real/script.sh")
        paths = ScriptPaths(scan=missing, email=missing, tweet=missing)
        result = execute_action("scan", "MSFT", paths=paths)
        self.assertFalse(result["success"])
        self.assertIn("script not found", result["error"])


if __name__ == "__main__":
    unittest.main()
