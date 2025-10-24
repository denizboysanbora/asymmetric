# Gmail API Setup Guide

## Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select an existing one)
3. Name it something like "Analyst Email Sender"

## Step 2: Enable Gmail API

1. In the Google Cloud Console, go to **APIs & Services** > **Library**
2. Search for "Gmail API"
3. Click on it and press **Enable**

## Step 3: Configure OAuth Consent Screen

1. Go to **APIs & Services** > **OAuth consent screen**
2. Choose **External** (unless you have a Google Workspace account)
3. Fill in required fields:
   - App name: "Analyst Email Sender"
   - User support email: Your email
   - Developer contact: Your email
4. Click **Save and Continue**
5. On the Scopes page, click **Add or Remove Scopes**
6. Search for and add: `https://www.googleapis.com/auth/gmail.send`
7. Click **Update** and then **Save and Continue**
8. Add your email as a test user
9. Click **Save and Continue**

## Step 4: Create OAuth Credentials

1. Go to **APIs & Services** > **Credentials**
2. Click **Create Credentials** > **OAuth client ID**
3. Application type: **Desktop app**
4. Name: "Analyst Desktop Client"
5. Click **Create**
6. Click **Download JSON** (download icon)
7. Save the downloaded file as `credentials.json` in this directory:
   `/Users/deniz/Documents/GitHub/asymmetric/analyst/output/gmail/credentials.json`

## Step 5: Authenticate

Once you have the real credentials.json file:

```bash
cd /Users/deniz/Documents/GitHub/asymmetric/analyst
python3 output/gmail/scripts/gmail_auth.py
```

This will:
1. Open a browser window
2. Ask you to sign in to Google
3. Ask for permission to send emails
4. Save the token for future use

## Step 6: Test Email

```bash
python3 output/gmail/send_email.py "deniz@bora.box" "Test Signal" '$INTC 37.01 +2.1% | Range Breakout'
```

## Troubleshooting

### 400 Error
- Make sure you created a **Desktop app** (not Web application)
- Verify redirect_uris in credentials.json includes `http://localhost`

### 403 Error
- Make sure Gmail API is enabled
- Check that you added the correct scope: `gmail.send`
- Verify your email is added as a test user

### Token Expired
- Delete `token.json` and run the auth script again

