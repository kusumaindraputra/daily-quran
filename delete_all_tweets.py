"""
Delete tweets from the connected Twitter account using tweet IDs from
the Twitter/X data archive (tweets.js).

HOW TO GET THE ARCHIVE:
  1. x.com → Settings → Your Account → Download an archive of your data
  2. Wait for email (1-24 hours), download the ZIP
  3. Extract it, find tweets.js inside

USAGE:
  .venv/bin/python delete_all_tweets.py --archive ~/Downloads/twitter-archive/tweets.js --dry-run
  .venv/bin/python delete_all_tweets.py --archive ~/Downloads/twitter-archive/tweets.js

This is PERMANENT — cannot be undone.
"""

import json
import os
import sys
import time
from pathlib import Path

# --- load .env ---
SCRIPT_DIR = Path(__file__).resolve().parent
env_file = SCRIPT_DIR / ".env"
dotenv = {}
if env_file.exists():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            dotenv[k.strip()] = v.strip().strip('"').strip("'")

def _get(key: str) -> str:
    return os.environ.get(key) or dotenv.get(key, "")

# --- parse args ---
DRY_RUN = "--dry-run" in sys.argv
ARCHIVE_PATH = ""
if "--archive" in sys.argv:
    idx = sys.argv.index("--archive")
    if idx + 1 < len(sys.argv):
        ARCHIVE_PATH = os.path.expanduser(sys.argv[idx + 1])

if not ARCHIVE_PATH:
    print("Usage: .venv/bin/python delete_all_tweets.py --archive <path/to/tweets.js> [--dry-run]")
    print()
    print("  Download your Twitter archive from: x.com → Settings → Your Account → Download archive")
    print("  Then pass the tweets.js file from inside the ZIP.")
    sys.exit(1)

# --- load tweet IDs from archive ---
print(f"Reading archive: {ARCHIVE_PATH}")
raw = Path(ARCHIVE_PATH).read_text(encoding="utf-8")

# tweets.js format: window.YTD.tweets.part0 = [ ... ]
# Strip the JS variable assignment to get the JSON array
if "=" in raw:
    raw = raw.split("=", 1)[1].strip()
# Remove trailing semicolon if present
raw = raw.rstrip(";")

tweets_data = json.loads(raw)
print(f"  Found {len(tweets_data)} tweets in archive")

# Extract IDs (optionally filter by type)
tweet_list = []
for entry in tweets_data:
    tweet = entry.get("tweet", entry)  # handle both formats
    tid = tweet.get("id_str") or tweet.get("id")
    text = tweet.get("full_text", tweet.get("text", ""))
    created = tweet.get("created_at", "?")
    tweet_list.append({"id": str(tid), "text": text[:80], "created": created})

print(f"  Parsed {len(tweet_list)} tweet IDs")
print()

# --- auth ---
consumer_key = _get("TWITTER_CONSUMER_KEY")
consumer_secret = _get("TWITTER_CONSUMER_SECRET")
access_token = _get("TWITTER_ACCESS_TOKEN")
access_secret = _get("TWITTER_ACCESS_SECRET")

if not all([consumer_key, consumer_secret, access_token, access_secret]):
    print("Missing credentials. Check .env file.")
    sys.exit(1)

import tweepy

client = tweepy.Client(
    consumer_key=consumer_key,
    consumer_secret=consumer_secret,
    access_token=access_token,
    access_token_secret=access_secret,
)

# Verify
user = client.get_me()
username = user.data["username"]
print(f"Account: @{username}")
print()

if DRY_RUN:
    print("*** DRY RUN — no tweets will be deleted ***")
    print()
    print(f"Will delete {len(tweet_list)} tweets.")
    print()
    for t in tweet_list[:10]:
        print(f"  [DRY RUN] [{t['created']}] {t['text']}...")
    if len(tweet_list) > 10:
        print(f"  ... and {len(tweet_list)-10} more")
    print()
    print("Run WITHOUT --dry-run to actually delete.")
    sys.exit(0)

# --- confirm ---
print(f"About to PERMANENTLY delete {len(tweet_list)} tweets from @{username}")
print(f"This CANNOT be undone.")
resp = input("Type 'YES DELETE ALL' to proceed: ").strip()
if resp != "YES DELETE ALL":
    print("Aborted.")
    sys.exit(0)

# --- delete ---
print()
deleted = 0
errors = 0
start_time = time.time()

for i, t in enumerate(tweet_list):
    try:
        client.delete_tweet(t["id"])
        deleted += 1
        pct = (i + 1) / len(tweet_list) * 100
        eta = (time.time() - start_time) / (i + 1) * (len(tweet_list) - i - 1)
        print(f"  [{i+1}/{len(tweet_list)}] ✓ [{pct:.0f}%] [{t['created']}] {t['text']}... (ETA {eta/60:.0f}m)")
        time.sleep(0.8)  # rate limit safety
    except tweepy.errors.NotFound:
        print(f"  [{i+1}/{len(tweet_list)}] - Already deleted: {t['id']}")
        deleted += 1
    except Exception as e:
        print(f"  [{i+1}/{len(tweet_list)}] ✗ Error: {e}")
        errors += 1
        if "429" in str(e):
            print("    Rate limited! Waiting 60s...")
            time.sleep(60)

# --- summary ---
print(f"\n{'='*50}")
print(f"DONE — {deleted} tweets deleted, {errors} errors, {len(tweet_list)-deleted-errors} skipped")
