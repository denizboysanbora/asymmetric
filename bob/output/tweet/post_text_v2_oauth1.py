#!/usr/bin/env python3
"""
Twitter API v2 tweet posting script using OAuth 1.0a User Context
"""
import os
import sys
import json
import requests
from requests_oauthlib import OAuth1
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent
TOKEN_FILE = BASE_DIR / "token.json"

def load_credentials():
    """Load OAuth 1.0a credentials from token.json"""
    if not TOKEN_FILE.exists():
        print("Error: token.json not found")
        sys.exit(1)
    
    with open(TOKEN_FILE, 'r') as f:
        creds = json.load(f)
    
    return creds

def post_tweet_v2_oauth1(text):
    """Post a tweet using Twitter API v2 with OAuth 1.0a User Context"""
    try:
        creds = load_credentials()
        
        # Twitter API v2 endpoint
        url = "https://api.twitter.com/2/tweets"
        
        # OAuth 1.0a authentication
        auth = OAuth1(
            creds['consumer_key'],
            creds['consumer_secret'],
            creds['access_token'],
            creds['access_token_secret']
        )
        
        # Headers
        headers = {
            "Content-Type": "application/json"
        }
        
        # Payload
        payload = {
            "text": text
        }
        
        # Make request
        response = requests.post(url, headers=headers, json=payload, auth=auth)
        
        if response.status_code == 201:
            tweet_data = response.json()
            print(f"Tweet posted successfully: {tweet_data['data']['id']}")
            return True
        else:
            print(f"Error posting tweet: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"Error posting tweet: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: post_text_v2_oauth1.py <tweet_text>")
        sys.exit(1)
    
    tweet_text = sys.argv[1]
    success = post_tweet_v2_oauth1(tweet_text)
    sys.exit(0 if success else 1)
