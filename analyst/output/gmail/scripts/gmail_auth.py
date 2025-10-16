#!/usr/bin/env python3
import os
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

BASE_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = BASE_DIR / 'config'
TOKEN_PATH = CONFIG_DIR / 'token.json'
CREDS_PATH = CONFIG_DIR / 'credentials.json'
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

if __name__ == '__main__':
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDS_PATH.exists():
                raise SystemExit(f"Missing {CREDS_PATH}. Download OAuth client from Google Cloud and place it there.")
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_PATH), SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, 'w') as token:
            token.write(creds.to_json())
    print(f"Token saved to {TOKEN_PATH}")
