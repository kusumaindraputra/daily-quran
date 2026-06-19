"""
Daily posting script: Select a random standalone ayah and post to Twitter/X.

Usage: python3 post_daily.py [--dry-run] [--ayah 1:1]
  --dry-run    Print the tweet without actually posting
  --ayah KEY   Force a specific ayah (e.g. 1:1 for Al-Fatihah 1:1)
"""

import json
import os
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

SURAH_NAMES = {
    1: "Al-Fatihah", 2: "Al-Baqarah", 3: "Ali 'Imran", 4: "An-Nisa",
    5: "Al-Ma'idah", 6: "Al-An'am", 7: "Al-A'raf", 8: "Al-Anfal",
    9: "At-Tawbah", 10: "Yunus", 11: "Hud", 12: "Yusuf",
    13: "Ar-Ra'd", 14: "Ibrahim", 15: "Al-Hijr", 16: "An-Nahl",
    17: "Al-Isra", 18: "Al-Kahf", 19: "Maryam", 20: "Ta-Ha",
    21: "Al-Anbiya", 22: "Al-Hajj", 23: "Al-Mu'minun", 24: "An-Nur",
    25: "Al-Furqan", 26: "Ash-Shu'ara", 27: "An-Naml", 28: "Al-Qasas",
    29: "Al-'Ankabut", 30: "Ar-Rum", 31: "Luqman", 32: "As-Sajdah",
    33: "Al-Ahzab", 34: "Saba", 35: "Fatir", 36: "Ya-Sin",
    37: "As-Saffat", 38: "Sad", 39: "Az-Zumar", 40: "Ghafir",
    41: "Fussilat", 42: "Ash-Shura", 43: "Az-Zukhruf", 44: "Ad-Dukhan",
    45: "Al-Jathiyah", 46: "Al-Ahqaf", 47: "Muhammad", 48: "Al-Fath",
    49: "Al-Hujurat", 50: "Qaf", 51: "Adh-Dhariyat", 52: "At-Tur",
    53: "An-Najm", 54: "Al-Qamar", 55: "Ar-Rahman", 56: "Al-Waqi'ah",
    57: "Al-Hadid", 58: "Al-Mujadila", 59: "Al-Hashr", 60: "Al-Mumtahanah",
    61: "As-Saf", 62: "Al-Jumu'ah", 63: "Al-Munafiqun", 64: "At-Taghabun",
    65: "At-Talaq", 66: "At-Tahrim", 67: "Al-Mulk", 68: "Al-Qalam",
    69: "Al-Haqqah", 70: "Al-Ma'arij", 71: "Nuh", 72: "Al-Jinn",
    73: "Al-Muzzammil", 74: "Al-Muddaththir", 75: "Al-Qiyamah", 76: "Al-Insan",
    77: "Al-Mursalat", 78: "An-Naba", 79: "An-Nazi'at", 80: "'Abasa",
    81: "At-Takwir", 82: "Al-Infitar", 83: "Al-Mutaffifin", 84: "Al-Inshiqaq",
    85: "Al-Buruj", 86: "At-Tariq", 87: "Al-A'la", 88: "Al-Ghashiyah",
    89: "Al-Fajr", 90: "Al-Balad", 91: "Ash-Shams", 92: "Al-Layl",
    93: "Ad-Duha", 94: "Ash-Sharh", 95: "At-Tin", 96: "Al-'Alaq",
    97: "Al-Qadr", 98: "Al-Bayyinah", 99: "Az-Zalzalah", 100: "Al-'Adiyat",
    101: "Al-Qari'ah", 102: "At-Takathur", 103: "Al-'Asr", 104: "Al-Humazah",
    105: "Al-Fil", 106: "Quraysh", 107: "Al-Ma'un", 108: "Al-Kawthar",
    109: "Al-Kafirun", 110: "An-Nasr", 111: "Al-Masad", 112: "Al-Ikhlas",
    113: "Al-Falaq", 114: "An-Nas",
}

# Resolve paths relative to this script's directory
SCRIPT_DIR = Path(__file__).resolve().parent
STATE_FILE = SCRIPT_DIR / "state.json"
POOL_FILE = SCRIPT_DIR / "standalone_pool.json"
HISTORY_FILE = SCRIPT_DIR / "posted_history.json"


def load_json(path: str) -> dict:
    """Load a JSON file, return empty dict/list if not found."""
    if not os.path.exists(path):
        return {} if path == STATE_FILE else []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data):
    """Save data to a JSON file."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def pick_ayah(pool: list[dict], posted_keys: set[str], force_key: str = "") -> dict | None:
    """Pick a random ayah from the pool, or force a specific one by key."""
    # If a specific ayah is forced, find it (regardless of posted status)
    if force_key:
        match = next((a for a in pool if a["key"] == force_key), None)
        if match:
            return match
        print(f"  ⚠ Ayah {force_key} not in pool — falling back to random")

    available = [a for a in pool if a["key"] not in posted_keys]

    if not available:
        print("⚠ All ayahs in the pool have been posted! Resetting history...")
        posted_keys.clear()
        available = pool

    # Weight selection: prefer curated > juz30 > length_pass
    # This ensures the most quotable ayahs appear first over time
    curated = [a for a in available if a.get("reason") == "curated"]
    juz30 = [a for a in available if a.get("reason") == "juz30_or_fatihah"]
    length = [a for a in available if a.get("reason") == "length_pass"]

    # Weight: 60% curated, 30% juz30, 10% length_pass
    weights = [0.6, 0.3, 0.1]
    pools = [curated, juz30, length]
    # Remove empty pools
    active_pools = [(p, w) for p, w in zip(pools, weights) if p]
    if not active_pools:
        return random.choice(available)

    # Normalize weights
    total_w = sum(w for _, w in active_pools)
    normalized = [(p, w / total_w) for p, w in active_pools]

    # Pick from weighted pools
    r = random.random()
    cumulative = 0.0
    for pool_list, weight in normalized:
        cumulative += weight
        if r <= cumulative or weight == normalized[-1][1]:
            return random.choice(pool_list)

    return random.choice(available)


def format_tweet(ayah: dict) -> str:
    """Format an ayah into a tweet with Arabic + English + reference."""
    surah_num = ayah["surah"]
    ayah_num = ayah["ayah"]
    surah_name = SURAH_NAMES.get(surah_num, ayah["surah_name_en"])
    ar_text = ayah["ar_text"]
    en_text = ayah["en_text"]

    # Clean up: strip extra newlines from API response
    ar_text = ar_text.replace("\n", " ").strip()
    en_text = en_text.replace("\n", " ").strip()

    # English must come first so the tweet's base bidi direction is LTR.
    # Twitter treats the whole tweet as one paragraph; Arabic first sets RTL
    # base direction and reorders neutral chars (periods, quotes, emoji) to
    # wrong visual positions — unfixable with any bidi control characters.
    tweet = (
        f'"{en_text}"\n\n'
        f"{ar_text}\n\n"
        f"📖 {surah_name} ({surah_num}:{ayah_num})"
    )

    return tweet


def post_to_twitter(client, tweet_text: str) -> str:
    """Post a tweet and return the tweet ID."""
    response = client.create_tweet(text=tweet_text)
    return response.data["id"]


def main():
    dry_run = "--dry-run" in sys.argv

    # Parse --ayah <key>
    force_key = ""
    if "--ayah" in sys.argv:
        idx = sys.argv.index("--ayah")
        if idx + 1 < len(sys.argv):
            force_key = sys.argv[idx + 1]

    print("=" * 50)
    print(" Quran Daily — Post Ayah")
    print("=" * 50)

    # Load pool
    print("\n[1/4] Loading ayah pool...")
    pool = load_json(POOL_FILE)
    if not pool:
        print("ERROR: standalone_pool.json not found. Run fetch_quran.py first.")
        sys.exit(1)
    print(f"  Pool: {len(pool)} standalone ayahs")

    # Load state
    print("[2/4] Loading state...")
    state = load_json(STATE_FILE)
    posted_keys = set(state.get("posted_keys", []))
    streak = state.get("streak", 0)

    # Check if already posted today
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    last_post_date = state.get("last_post_date", "")
    if last_post_date == today and not dry_run:
        print(f"  ⚠ Already posted today ({today}). Use --dry-run to preview next.")
        print(f"  Current streak: {streak} day(s)")
        sys.exit(0)

    # Pick ayah
    print("[3/4] Selecting ayah...")
    if force_key:
        print(f"  Forcing ayah: {force_key}")
    ayah = pick_ayah(pool, posted_keys, force_key)
    if not ayah:
        print("ERROR: Could not select ayah.")
        sys.exit(1)
    print(f"  Selected: {ayah['key']} ({ayah['surah_name_en']})")
    print(f"  Reason:   {ayah.get('reason', 'unknown')}")

    # Format tweet
    tweet_text = format_tweet(ayah)
    print(f"\n{'─' * 40}")
    print(tweet_text)
    print(f"{'─' * 40}")
    print(f"  Character count: {len(tweet_text)}")

    if dry_run:
        print("\n  [DRY RUN] Not posted to Twitter.")
        return

    # Post to Twitter
    print("\n[4/4] Posting to Twitter/X...")
    try:
        import tweepy

        # Load credentials — env vars first, fallback to .env file
        def _load_env_file(path: Path) -> dict[str, str]:
            """Parse a simple KEY=VALUE .env file."""
            result = {}
            if path.exists():
                for line in path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        result[k.strip()] = v.strip().strip('"').strip("'")
            return result

        env_file = SCRIPT_DIR / ".env"
        dotenv = _load_env_file(env_file) if env_file.exists() else {}

        consumer_key = (
            os.environ.get("TWITTER_CONSUMER_KEY")
            or dotenv.get("TWITTER_CONSUMER_KEY")
            or os.environ.get("TWITTER_API_KEY")
        )
        consumer_secret = (
            os.environ.get("TWITTER_CONSUMER_SECRET")
            or dotenv.get("TWITTER_CONSUMER_SECRET")
            or os.environ.get("TWITTER_API_SECRET")
        )
        access_token = (
            os.environ.get("TWITTER_ACCESS_TOKEN")
            or dotenv.get("TWITTER_ACCESS_TOKEN")
        )
        access_secret = (
            os.environ.get("TWITTER_ACCESS_SECRET")
            or dotenv.get("TWITTER_ACCESS_SECRET")
        )

        if not all([consumer_key, consumer_secret, access_token, access_secret]):
            print("  ✗ Missing Twitter credentials!")
            print("  Set env vars or create .env file with:")
            print("    TWITTER_CONSUMER_KEY=...")
            print("    TWITTER_CONSUMER_SECRET=...")
            print("    TWITTER_ACCESS_TOKEN=...")
            print("    TWITTER_ACCESS_SECRET=...")
            sys.exit(1)

        client = tweepy.Client(
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            access_token=access_token,
            access_token_secret=access_secret,
        )
        tweet_id = post_to_twitter(client, tweet_text)
        print(f"  ✓ Posted! Tweet ID: {tweet_id}")

        # Update state
        posted_keys.add(ayah["key"])
        if last_post_date:
            last_date = datetime.strptime(last_post_date, "%Y-%m-%d")
            today_date = datetime.strptime(today, "%Y-%m-%d")
            diff = (today_date - last_date).days
            if diff == 1:
                streak += 1
            elif diff > 1:
                streak = 1  # Break in streak
        else:
            streak = 1

        state["last_post_date"] = today
        state["posted_keys"] = list(posted_keys)
        state["streak"] = streak
        state["last_ayah"] = ayah["key"]
        state["total_posts"] = state.get("total_posts", 0) + 1
        save_json(STATE_FILE, state)

        # Append to history log
        history = load_json(HISTORY_FILE)
        history.append({
            "date": today,
            "key": ayah["key"],
            "tweet_id": tweet_id,
            "tweet_text": tweet_text,
        })
        save_json(HISTORY_FILE, history)

        print(f"  Streak: {streak} day(s)")
        print(f"  Total posts: {state['total_posts']}")

    except Exception as e:
        # Handle tweepy errors even though tweepy may not be imported yet
        err_msg = str(e)
        if hasattr(e, 'response') and e.response is not None:
            status = getattr(e.response, 'status_code', 0)
            if status == 403:
                print(f"  ✗ Twitter API error (Forbidden/403): {err_msg}")
                print("  Check your API credentials and app permissions.")
                sys.exit(1)
            elif status == 401:
                print(f"  ✗ Twitter API error (Unauthorized/401): {err_msg}")
                print("  Check your API Key and Secret.")
                sys.exit(1)
        print(f"  ✗ Error posting: {err_msg}")
        sys.exit(1)
        sys.exit(1)

    print("\n✓ Done!")


if __name__ == "__main__":
    main()
