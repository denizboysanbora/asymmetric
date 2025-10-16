# Bob GitHub Secrets Setup Guide

This guide will help you configure all the necessary secrets for Bob to run on GitHub Actions.

## 🔐 Required Secrets

You need to add the following secrets to your GitHub repository:

### 1. Alpaca API Secrets
- `ALPACA_API_KEY` - Your Alpaca API key
- `ALPACA_SECRET_KEY` - Your Alpaca secret key

### 2. Supabase Database Secrets
- `SUPABASE_URL` - Your Supabase project URL
- `SUPABASE_SERVICE_KEY` - Your Supabase service role key

### 3. Gmail Notification Secrets
- `GMAIL_CLIENT_ID` - Gmail OAuth client ID
- `GMAIL_CLIENT_SECRET` - Gmail OAuth client secret
- `GMAIL_REFRESH_TOKEN` - Gmail refresh token

### 4. Twitter Notification Secrets
- `TWITTER_API_KEY` - Twitter API key
- `TWITTER_API_SECRET` - Twitter API secret
- `TWITTER_ACCESS_TOKEN` - Twitter access token
- `TWITTER_ACCESS_SECRET` - Twitter access secret

## 📋 Step-by-Step Setup

### Step 1: Access Repository Settings

1. Go to your GitHub repository
2. Click on **Settings** tab
3. In the left sidebar, click **Secrets and variables** → **Actions**

### Step 2: Add Each Secret

For each secret below, click **New repository secret** and add:

#### Alpaca API
```
Name: ALPACA_API_KEY
Value: [Your Alpaca API key from config/api_keys.env]
```

```
Name: ALPACA_SECRET_KEY
Value: [Your Alpaca secret key from config/api_keys.env]
```

#### Supabase Database
```
Name: SUPABASE_URL
Value: https://nxxhdueqvbsogpzxdmlb.supabase.co
```

```
Name: SUPABASE_SERVICE_KEY
Value: [Your Supabase service key]
```

#### Gmail Notifications
```
Name: GMAIL_CLIENT_ID
Value: [Your Gmail client ID from config/api_keys.env]
```

```
Name: GMAIL_CLIENT_SECRET
Value: [Your Gmail client secret from config/api_keys.env]
```

```
Name: GMAIL_REFRESH_TOKEN
Value: [Your Gmail refresh token from config/api_keys.env]
```

#### Twitter Notifications
```
Name: TWITTER_API_KEY
Value: [Your Twitter API key from config/api_keys.env]
```

```
Name: TWITTER_API_SECRET
Value: [Your Twitter API secret from config/api_keys.env]
```

```
Name: TWITTER_ACCESS_TOKEN
Value: [Your Twitter access token from config/api_keys.env]
```

```
Name: TWITTER_ACCESS_SECRET
Value: [Your Twitter access secret from config/api_keys.env]
```

## 🔍 Finding Your API Keys

### From Local Config
Check your `analyst/config/api_keys.env` file for the values:

```bash
cd /Users/deniz/Code/asymmetric/analyst
cat config/api_keys.env
```

### Alpaca API
- Get from: https://app.alpaca.markets/paper/dashboard/overview
- Copy your API Key and Secret Key

### Supabase
- Get from: https://supabase.com/dashboard/project/nxxhdueqvbsogpzxdmlb/settings/api
- Copy the Project URL and Service Role Key

### Gmail API
- Get from: https://console.developers.google.com/apis/credentials
- Copy Client ID, Client Secret, and generate Refresh Token

### Twitter API
- Get from: https://developer.twitter.com/en/portal/dashboard
- Copy API Key, API Secret, Access Token, and Access Secret

## ✅ Verification

### Check Secrets Are Set
1. Go to **Settings** → **Secrets and variables** → **Actions**
2. Verify all 10 secrets are listed
3. Make sure they're not empty

### Test the Workflow
1. Go to **Actions** tab
2. Click **Test Bob Analyst**
3. Click **Run workflow**
4. Monitor the execution logs

## 🚨 Troubleshooting

### Common Issues

1. **Secret Not Found Error**:
   - Double-check secret names (case-sensitive)
   - Ensure secrets are added to the correct repository
   - Verify you have admin access to the repository

2. **Authentication Errors**:
   - Verify API keys are correct
   - Check if keys have expired
   - Ensure proper permissions are granted

3. **Workflow Not Running**:
   - Check if GitHub Actions is enabled
   - Verify repository permissions
   - Check if workflows are in the correct directory

### Getting Help

- **GitHub Actions Logs**: Check execution logs for specific errors
- **Secret Management**: Review GitHub documentation on secrets
- **API Documentation**: Check individual API documentation for key formats

## 🔒 Security Best Practices

1. **Never commit secrets to code**
2. **Use repository secrets, not environment variables**
3. **Rotate API keys regularly**
4. **Monitor secret usage**
5. **Use least-privilege access**

## 📊 Monitoring

### Check Secret Usage
1. Go to **Actions** tab
2. Click on any workflow run
3. Check the logs for secret-related errors
4. Verify all secrets are being used correctly

### Test Individual Components
You can test each component separately by creating test workflows that only use specific secrets.

## 🎯 Next Steps

After setting up all secrets:

1. **Test the System**: Run the test workflow
2. **Monitor Execution**: Check the main workflow
3. **Verify Notifications**: Ensure emails and tweets are sent
4. **Check Database**: Verify signals are logged to Supabase
5. **Optimize**: Fine-tune the system based on results

Bob is now ready to run on GitHub Actions! 🚀
