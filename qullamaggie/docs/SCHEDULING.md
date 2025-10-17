# Qullamaggie Scheduling

## ⏰ Automatic Cron Scheduling

Qullamaggie is configured to run automatically via cron job during market hours.

### Schedule Details

- **Operating Hours**: 8 AM - 4 PM Eastern Time
- **Frequency**: Every 30 minutes
- **Days**: Monday - Friday (weekdays only)
- **Timezone**: Eastern Time (system timezone)

### Cron Expression

```bash
0,30 8-16 * * 1-5 /Users/deniz/Code/asymmetric/qullamaggie/qullamaggie.sh
```

**Breakdown:**
- `0,30`: Every 0 and 30 minutes (8:00, 8:30, 9:00, 9:30, etc.)
- `8-16`: 8 AM - 4 PM (16:00)
- `* *`: Every day of month, every month
- `1-5`: Monday through Friday (1=Monday, 5=Friday)

### Analysis Types by Time

#### Pre-Market Analysis (8:00 AM - 9:30 AM)
- **Purpose**: Generate momentum watchlist
- **Actions**: 
  - Scan for Qullamaggie Breakout, Episodic, and Parabolic setups
  - Check market gate (QQQ 10/20 EMA trend)
  - Send watchlist email if candidates found

#### Opening Range Analysis (9:35 AM - 4:00 PM)
- **Purpose**: Monitor for breakout triggers
- **Actions**:
  - Analyze opening range breakouts
  - Check entry triggers for detected setups
  - Send breakout alert emails if triggered

#### Market Open Buffer (9:30 AM - 9:35 AM)
- **Purpose**: Allow opening range data to accumulate
- **Actions**: Skip analysis (waiting period)

## 🔧 Management Commands

### View Current Cron Jobs
```bash
crontab -l
```

### Edit Cron Jobs
```bash
crontab -e
```

### Check Qullamaggie Status
```bash
./status.sh
```

### Manual Execution (for testing)
```bash
./qullamaggie.sh
```

## 📊 Monitoring

### Log Files
- **Location**: `logs/qullamaggie.log`
- **Content**: Detailed execution logs with timestamps
- **Rotation**: Manual cleanup required

### Email Notifications
- **Pre-market**: Watchlist emails sent to `deniz@bora.box`
- **Intraday**: Breakout alert emails sent when triggers hit
- **Subject Lines**: "Qullamaggie Watchlist" or "Qullamaggie Breakouts"

## 🆚 Comparison with Other Systems

| System | Schedule | Frequency | Purpose |
|--------|----------|-----------|---------|
| **Qullamaggie** | 8 AM - 4 PM ET | Every 30 min | Momentum setups |
| **Analyst** | 10 AM - 4 PM ET | Every 30 min | Breakout/trend signals |
| **Investor** | 24/7 | Every 5 min | Trading execution |

## ✅ Verification

To verify the cron job is working:

1. **Check cron status**:
   ```bash
   crontab -l | grep qullamaggie
   ```

2. **Test manual execution**:
   ```bash
   ./qullamaggie.sh
   ```

3. **Monitor logs**:
   ```bash
   tail -f logs/qullamaggie.log
   ```

4. **Check during market hours**: The script will run automatically and send emails if signals are detected.
