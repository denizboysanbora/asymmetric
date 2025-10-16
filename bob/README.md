# Bob - GitHub Actions Market Analyst

Bob is a cloud-based version of the analyst system that runs on GitHub Actions instead of locally. It provides the same market analysis functionality with the benefits of cloud execution and automatic scaling.

## 🏗️ Architecture

- **GitHub Actions**: Cloud-based execution environment
- **Cron Scheduling**: Automatic execution every 30 minutes during market hours
- **Python Environment**: Same codebase as local analyst
- **Secrets Management**: Secure API key storage via GitHub Secrets

## 🚀 Features

- ✅ **Cloud Execution**: Runs on GitHub Actions infrastructure
- ✅ **Cron Scheduling**: Every 30 minutes (10 AM - 4 PM ET)
- ✅ **Same Codebase**: Uses existing analyst Python code
- ✅ **Automatic Scaling**: GitHub handles infrastructure
- ✅ **Secure Secrets**: API keys stored in GitHub Secrets
- ✅ **Logging**: Built-in GitHub Actions logging
- ✅ **Manual Triggers**: Can be triggered manually for testing

## 📁 File Structure

```
bob/
├── .github/workflows/
│   ├── bob-worker.yml      # Main cron job workflow
│   └── test-bob.yml        # Testing workflow
├── analyst.py              # Main Bob analyst script
├── requirements.txt        # Python dependencies
├── config/                 # Configuration files
├── input/                  # Market data input modules
├── output/                 # Notification and database modules
├── logs/                   # Log files
└── README.md              # This file
```

## ⚙️ Setup

### 1. GitHub Secrets Configuration

Add the following secrets to your GitHub repository:

**Alpaca API:**
- `ALPACA_API_KEY`
- `ALPACA_SECRET_KEY`

**Supabase Database:**
- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`

**Gmail Notifications:**
- `GMAIL_CLIENT_ID`
- `GMAIL_CLIENT_SECRET`
- `GMAIL_REFRESH_TOKEN`

**Twitter Notifications:**
- `TWITTER_API_KEY`
- `TWITTER_API_SECRET`
- `TWITTER_ACCESS_TOKEN`
- `TWITTER_ACCESS_SECRET`

### 2. Enable GitHub Actions

1. Go to your repository on GitHub
2. Click on "Actions" tab
3. Enable GitHub Actions if not already enabled
4. The workflows will automatically start running

### 3. Test the System

1. **Manual Test**: Go to Actions → "Test Bob Analyst" → "Run workflow"
2. **Cron Test**: Wait for the scheduled time or manually trigger "Bob Market Analyst Worker"

## ⏰ Schedule

- **Market Hours**: 10 AM - 4 PM Eastern Time
- **Frequency**: Every 30 minutes
- **Days**: Monday - Friday
- **Timezone**: UTC (GitHub Actions runs in UTC)

## 🔧 Workflow Details

### Main Worker (`bob-worker.yml`)
- **Trigger**: Cron schedule + manual dispatch
- **Schedule**: `0,30 15-21 * * 1-5` (10 AM - 4 PM ET)
- **Environment**: Ubuntu latest
- **Steps**:
  1. Checkout code
  2. Set up Python 3.11
  3. Install dependencies
  4. Run Bob analyst
  5. Upload logs

### Test Workflow (`test-bob.yml`)
- **Trigger**: Push/PR to main branch + manual dispatch
- **Purpose**: Test Bob functionality
- **Steps**:
  1. Checkout code
  2. Set up Python 3.11
  3. Install dependencies
  4. Run tests
  5. Upload results

## 📊 Monitoring

### GitHub Actions Dashboard
- **Workflow Runs**: View execution history
- **Logs**: Real-time execution logs
- **Artifacts**: Download log files
- **Status**: Success/failure indicators

### Log Files
- **Location**: `bob/logs/bob.log`
- **Content**: Detailed execution logs
- **Retention**: Available as GitHub Actions artifacts

## 🆚 Bob vs Local Analyst

| Feature | Local Analyst | Bob (GitHub Actions) |
|---------|---------------|----------------------|
| **Execution** | Your machine | GitHub Actions |
| **Scheduling** | Cron job | GitHub Actions cron |
| **Dependencies** | Local Python | GitHub Actions Python |
| **Monitoring** | Local logs | GitHub Actions logs |
| **Scaling** | Single machine | GitHub infrastructure |
| **Maintenance** | Manual updates | Automatic deployments |
| **Cost** | Free (your hardware) | GitHub Actions minutes |
| **Reliability** | Depends on your machine | 99.9% uptime |
| **Secrets** | Local files | GitHub Secrets |

## 🧪 Testing

### Local Testing
```bash
cd bob
python analyst.py
```

### GitHub Actions Testing
1. Go to Actions tab
2. Select "Test Bob Analyst"
3. Click "Run workflow"
4. Monitor execution logs

### Manual Trigger
1. Go to Actions tab
2. Select "Bob Market Analyst Worker"
3. Click "Run workflow"
4. Monitor execution

## 🔧 Development

### Making Changes
1. **Edit Code**: Modify files in the `bob/` directory
2. **Test Locally**: Run `python analyst.py`
3. **Commit Changes**: Push to main branch
4. **Monitor**: Check GitHub Actions for execution

### Debugging
1. **Check Logs**: View GitHub Actions logs
2. **Download Artifacts**: Get log files
3. **Test Workflow**: Use test workflow for debugging
4. **Manual Trigger**: Test with manual workflow runs

## 📈 Benefits

### 🎯 **Reliability**
- GitHub's 99.9% uptime SLA
- No dependency on your local machine
- Automatic retry on failures

### 🚀 **Scalability**
- GitHub handles infrastructure scaling
- No resource constraints
- Global distribution

### 🔧 **Maintenance**
- No local dependencies to manage
- Automatic code deployments
- Built-in monitoring and logging

### 💰 **Cost Efficiency**
- Pay only for GitHub Actions minutes used
- No hardware maintenance
- Reduced operational overhead

### 🔒 **Security**
- GitHub Secrets for API keys
- Secure execution environment
- No local credential storage

## 🚨 Troubleshooting

### Common Issues

1. **Workflow Not Running**:
   - Check if GitHub Actions is enabled
   - Verify cron schedule is correct
   - Check repository permissions

2. **Authentication Errors**:
   - Verify all secrets are set correctly
   - Check API key permissions
   - Test individual components

3. **Import Errors**:
   - Ensure all dependencies are in requirements.txt
   - Check Python path configuration
   - Verify file structure

4. **Market Hours Issues**:
   - Check timezone configuration
   - Verify cron schedule matches ET
   - Test timezone conversion

### Getting Help

- **GitHub Actions Logs**: Check execution logs for errors
- **Local Testing**: Test components locally first
- **Documentation**: Review analyst documentation
- **Issues**: Create GitHub issues for bugs

## 🔮 Future Enhancements

- **Multi-timeframe Analysis**: 1min, 5min, 15min charts
- **Advanced Notifications**: Slack, Discord, webhooks
- **Portfolio Integration**: Connect with investor mode
- **Custom Alerts**: Configurable signal thresholds
- **Dashboard**: Real-time monitoring interface
- **Backtesting**: Historical signal analysis

## 🎉 Conclusion

Bob provides a robust, cloud-based alternative to your local analyst system. It maintains all the functionality while adding reliability, scalability, and ease of maintenance. The GitHub Actions platform provides enterprise-grade infrastructure with built-in monitoring and logging.

**Next Steps:**
1. Configure GitHub Secrets
2. Enable GitHub Actions
3. Test the system
4. Monitor execution
5. Optimize and enhance

Bob is ready to revolutionize your market analysis workflow! 🚀