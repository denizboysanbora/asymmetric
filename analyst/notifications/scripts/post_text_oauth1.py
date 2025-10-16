#!/usr/bin/env python3
import os
import sys
import json
from dotenv import load_dotenv
import requests
from requests_oauthlib import OAuth1

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BASE_DIR, 'config', '.env')
load_dotenv(ENV_PATH)

API_KEY = os.getenv('X_API_KEY')
API_KEY_SECRET = os.getenv('X_API_KEY_SECRET')
ACCESS_TOKEN = os.getenv('X_ACCESS_TOKEN')
ACCESS_TOKEN_SECRET = os.getenv('X_ACCESS_TOKEN_SECRET')

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: post_text_oauth1.py "tweet text"', file=sys.stderr)
        sys.exit(2)
    text = sys.argv[1]
    if not (API_KEY and API_KEY_SECRET and ACCESS_TOKEN and ACCESS_TOKEN_SECRET):
        print('Missing OAuth1.0a credentials in config/.env', file=sys.stderr)
        sys.exit(2)
    url = 'https://api.twitter.com/2/tweets'
    auth = OAuth1(API_KEY, API_KEY_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
    resp = requests.post(url, json={'text': text}, auth=auth, timeout=20)
    if resp.status_code == 429:
        print('Rate limited (HTTP 429). Try again later.', file=sys.stderr)
        sys.exit(1)
    resp.raise_for_status()
    print(json.dumps(resp.json(), indent=2))
