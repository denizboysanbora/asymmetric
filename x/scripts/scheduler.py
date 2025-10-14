#!/usr/bin/env python3
import argparse
import os
import signal
import sys
import time
from typing import Any, Dict, List

import yaml
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import requests

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(BASE_DIR, 'scripts')


def load_config(path: str) -> Dict[str, Any]:
    with open(path, 'r') as f:
        data = yaml.safe_load(f) or {}
    return data


def post_text(text: str) -> None:
    import subprocess
    subprocess.run([
        os.path.join(BASE_DIR, 'venv', 'bin', 'python'),
        os.path.join(SCRIPTS_DIR, 'post_text_oauth1.py'),
        text
    ], check=False)


def post_from_file(path: str) -> None:
    try:
        with open(path, 'r') as f:
            text = f.read().strip()
        if text:
            post_text(text)
    except Exception as e:
        print(f'Failed to post from file {path}: {e}', file=sys.stderr)


def schedule_jobs(sched: BackgroundScheduler, cfg: Dict[str, Any]) -> None:
    schedules: List[Dict[str, Any]] = cfg.get('schedules') or []
    for job in schedules:
        if not job.get('enabled', True):
            continue
        cron_expr = job.get('cron')
        if not cron_expr:
            print(f"Skipping job without cron: {job}")
            continue
        parts = cron_expr.split()
        if len(parts) != 5:
            print(f"Invalid cron expression (need 5 parts): {cron_expr}")
            continue
        minute, hour, day, month, weekday = parts
        trigger = CronTrigger(minute=minute, hour=hour, day=day, month=month, day_of_week=weekday)

        job_type = job.get('type', 'text')
        if job_type == 'text':
            text = job.get('text', '')
            sched.add_job(post_text, trigger=trigger, args=[text], id=job.get('id'))
        elif job_type == 'file':
            path = job.get('path')
            sched.add_job(post_from_file, trigger=trigger, args=[path], id=job.get('id'))
        elif job_type == 'btc_change':
            # Compose BTC last-hour tweet and post only if signal threshold met
            def run_btc_change():
                import subprocess, json
                # First, get text only (no API call)
                res = subprocess.run([
                    os.path.join(BASE_DIR, 'venv', 'bin', 'python'),
                    os.path.join(SCRIPTS_DIR, 'tweet_btc_change.py')
                ], capture_output=True, text=True)
                # Parse the printed line following 'Tweet text:'
                lines = res.stdout.strip().splitlines()
                text_line = ''
                for i, line in enumerate(lines):
                    if line.strip() == 'Tweet text:' and i + 1 < len(lines):
                        text_line = lines[i + 1].strip()
                        break
                # Extract percent from format: "$BTC +/-xx.xx% $price"
                # Decide threshold from config (default 0.10%)
                threshold_pct = float((cfg.get('signals') or {}).get('btc_change_threshold_pct', 0.10))
                try:
                    pct_part = text_line.split()[1]  # like +0.15%
                    pct_val = float(pct_part.replace('%', ''))
                except Exception:
                    pct_val = 0.0
                if abs(pct_val) >= threshold_pct:
                    # Post
                    subprocess.run([
                        os.path.join(BASE_DIR, 'venv', 'bin', 'python'),
                        os.path.join(SCRIPTS_DIR, 'tweet_btc_change.py'),
                        '--post'
                    ], check=False)
            sched.add_job(run_btc_change, trigger=trigger, id=job.get('id'))
        else:
            print(f"Unknown job type: {job_type}")


def main() -> None:
    parser = argparse.ArgumentParser(description='Run cron-like scheduler for X posting')
    parser.add_argument('--config', default=os.path.join(BASE_DIR, 'schedule.yaml'))
    args = parser.parse_args()

    cfg = load_config(args.config)
    timezone = cfg.get('timezone')

    scheduler = BackgroundScheduler(timezone=timezone)
    scheduler.start()

    schedule_jobs(scheduler, cfg)

    print('Scheduler started. Press Ctrl+C to exit.')

    def handle(sig, frame):
        print('Shutting down...')
        scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGINT, handle)
    signal.signal(signal.SIGTERM, handle)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        handle(None, None)


if __name__ == '__main__':
    main()
