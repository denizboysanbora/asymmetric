#!/usr/bin/env python3
"""
Gmail OAuth2 authentication setup
"""

import os
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# Gmail API scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

def authenticate_gmail():
    """Authenticate with Gmail API and save credentials"""
    
    # Paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    token_path = os.path.join(parent_dir, 'token.json')
    credentials_path = os.path.join(parent_dir, 'credentials.json')
    
    creds = None
    
    # Check if token exists
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    
    # If no valid credentials, get new ones
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(credentials_path):
                print("❌ credentials.json not found!")
                print("Please download your OAuth2 credentials from Google Cloud Console")
                print("and save them as 'credentials.json' in the gmail directory")
                return False
                
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save credentials for next time
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
        print(f"✅ Credentials saved to {token_path}")
    
    return True

if __name__ == "__main__":
    print("🔐 Setting up Gmail authentication...")
    if authenticate_gmail():
        print("✅ Gmail authentication successful!")
    else:
        print("❌ Gmail authentication failed!")