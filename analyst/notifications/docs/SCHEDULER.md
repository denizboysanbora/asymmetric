# Python Scheduler (APScheduler) for X Posting

- Uses APScheduler CronTrigger to mimic cron behavior
- Reads `schedule.yaml`
- Spawns `post_text_oauth1.py` using the venv Python

## YAML format

See `../schedule.yaml` and examples in plan. Cron is five fields: `min hour day month weekday`.

## Start scheduler

```bash
cd /Users/deniz/Library/CloudStorage/Dropbox/Bora/Code/asymmetric/x
./venv/bin/python scripts/scheduler.py --config schedule.yaml
```

## Logs

Redirect output as needed, e.g.:

```bash
./venv/bin/python scripts/scheduler.py --config schedule.yaml >> logs/scheduler.log 2>&1
```

## Troubleshooting
- Verify `config/.env` has valid OAuth 1.0a keys (`X_API_KEY`, etc.)
- Check cron expressions are valid (5 fields)
- Long-running tasks: prefer BackgroundScheduler to avoid blocking
- Timezone: set `timezone` in YAML or rely on system default
