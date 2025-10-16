#!/usr/bin/env python3
"""
Simple Twitter OAuth1 posting script
"""
import os
import sys
import json
from pathlib import Path
import tweepy

# Paths
BASE_DIR = Path(__file__).parent
TOKEN_FILE = BASE_DIR / "token.json"

def load_credentials():
    """Load Twitter API credentials from token.json"""
    if not TOKEN_FILE.exists():
        print("Error: token.json not found")
        sys.exit(1)
    
    with open(TOKEN_FILE, 'r') as f:
        creds = json.load(f)
    
    return creds

def post_tweet(text):
    """Post a tweet using OAuth1"""
    try:
        creds = load_credentials()
        
        # Initialize OAuth1 handler
        auth = tweepy.OAuth1UserHandler(
            creds['consumer_key'],
            creds['consumer_secret'],
            creds['access_token'],
            creds['access_token_secret']
        )
        
        # Create API object
        api = tweepy.API(auth)
        
        # Post tweet
        response = api.update_status(status=text)
        print(f"Tweet posted successfully: {response.id}")
        return True
        
    except Exception as e:
        print(f"Error posting tweet: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: post_text_oauth1.py <tweet_text>")
        sys.exit(1)
    
    tweet_text = sys.argv[1]
    success = post_tweet(tweet_text)
    sys.exit(0 if success else 1)

