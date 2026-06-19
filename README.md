# Quran Daily — 1 Day 1 Ayat 🤖📖

Automated Twitter/X bot that posts one Quran verse daily — Arabic text + English
translation (Sahih International). Runs on GitHub Actions, completely free.

## Features

- **Random standalone ayahs** — curated pool of ~2759 self-contained verses
- **Arabic + English** — Uthmani script + Sahih International translation
- **Smart filtering** — skips mid-context fragments, connector words, too-long ayahs
- **Streak tracking** — counts consecutive daily posts
- **Weighted selection** — 60% curated iconic ayahs, 30% Juz 30, 10% others
- **Auto-commit** — post state tracked in git, no server needed

## Setup (15 minutes)

### 1. Twitter/X API Credentials

Go to **https://console.x.com** (was developer.twitter.com) → sign in with your verified account.

#### Create a Project & App

1. Click **"Create Project"** → name it "Quran Daily"
2. Click **"Create App"** → name it "Quran Daily Bot"
3. In **User authentication settings**:
   - App permissions: **Read and Write**
   - Type of App: **Web App, Automated App or Bot**
   - Callback URL: `https://example.com` (placeholder, not used)
   - Website URL: your GitHub repo URL (optional)

#### Get Your Keys

You'll see these sections in the app dashboard:

| Section | Keys You Need | Env Var Name |
|---------|--------------|--------------|
| **OAuth 1.0a Keys** | Consumer Key (API Key) | `TWITTER_CONSUMER_KEY` |
| | Consumer Secret (API Key Secret) | `TWITTER_CONSUMER_SECRET` |

> **OAuth 1.0a** is the simplest for bots — generate access tokens once, use forever.
> OAuth 2.0 (Client ID + Client Secret) is also available but requires PKCE flow
> and periodic token refresh, which adds complexity for automation.

#### Generate Access Token

Under **OAuth 1.0a Keys** section:
1. Click **"Generate Access Token and Secret"**
2. You'll get two more values:

| Value | Env Var Name |
|-------|-------------|
| Access Token | `TWITTER_ACCESS_TOKEN` |
| Access Token Secret | `TWITTER_ACCESS_SECRET` |

Now you have all 4 keys needed.

> **Note:** With Twitter Blue (verified), your bot posts up to 25,000 chars.
> The free API tier (500 posts/month) is plenty for 1 post/day.

### 2. Create GitHub Repository

```bash
cd ~/Projects/daily-quran
git init
git add .
git commit -m "feat: daily quran bot setup"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/daily-quran.git
git push -u origin main
```

### 3. Add Secrets to GitHub

Go to your repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**.

Add these 4 secrets:

| Secret Name | Value (from console.x.com) |
|-------------|---------------------------|
| `TWITTER_CONSUMER_KEY` | OAuth 1.0a Consumer Key (API Key) |
| `TWITTER_CONSUMER_SECRET` | OAuth 1.0a Consumer Secret (API Key Secret) |
| `TWITTER_ACCESS_TOKEN` | Generated Access Token |
| `TWITTER_ACCESS_SECRET` | Generated Access Token Secret |

### 4. Generate Quran Data

```bash
# Setup virtual environment
python3 -m venv .venv

# Install dependencies
.venv/bin/pip install tweepy requests

# Fetch Quran dataset + generate standalone pool
.venv/bin/python fetch_quran.py
```

This downloads all 6236 ayahs from `api.alquran.cloud` (free, no key needed) and creates:
- `quran_full.json` — complete Quran (~3 MB)
- `standalone_pool.json` — filtered standalone ayahs (~500 KB)

### 5. Test a Post

```bash
# Dry run — preview without posting
.venv/bin/python post_daily.py --dry-run

# First post: Al-Fatihah 1:1
export TWITTER_CONSUMER_KEY="your_consumer_key"
export TWITTER_CONSUMER_SECRET="your_consumer_secret"
export TWITTER_ACCESS_TOKEN="your_access_token"
export TWITTER_ACCESS_SECRET="your_access_token_secret"

.venv/bin/python post_daily.py --ayah 1:1
```

### 6. Push Data Files

```bash
git add quran_full.json standalone_pool.json
git commit -m "data: quran dataset + standalone pool"
git push
```

### 7. Test GitHub Actions

Go to your repo → **Actions** → **Daily Quran Post** → **Run workflow**.
This triggers a manual run without waiting for the cron schedule.

---

## How It Works

```
┌─────────────────────────────────────────────────┐
│  GitHub Actions (cron: daily 6 AM WIB)           │
│                                                   │
│  1. Checkout repo                                 │
│  2. pip install tweepy                            │
│  3. python post_daily.py                          │
│     ├── Load standalone_pool.json (~2759 ayahs)  │
│     ├── Load state.json (posted history)          │
│     ├── Weighted random pick (unposted ayahs)     │
│     ├── Format: Arabic + English + reference      │
│     ├── Post via Twitter API v2 (OAuth 1.0a)     │
│     └── Save state + commit back to repo          │
└─────────────────────────────────────────────────┘
```

## Pool Breakdown

| Category | Count | Description |
|----------|-------|-------------|
| Curated | 157 | Iconic, frequently-quoted standalone ayahs |
| Juz 30 + Al-Fatihah | 529 | Short surahs — almost all self-contained |
| Length/context pass | 2,073 | Ayahs from longer surahs that pass standalone heuristics |
| **Total pool** | **~2,759** | **~7.5 years of daily content** |
| Skipped: too long | 402 | Combined Arabic+English > 600 chars |
| Skipped: connector start | 3,075 | Starts with وَ / فَ / etc. |

## Authentication: OAuth 1.0a vs OAuth 2.0

| | OAuth 1.0a | OAuth 2.0 |
|---|---|---|
| **Setup** | Generate token once | PKCE flow, refresh tokens |
| **Token lifetime** | Never expires | Refreshes every 2 hours |
| **Best for** | **Bots, automation** | User-facing apps |
| **Keys needed** | 4 keys (consumer + access) | Client ID + Secret + refresh token |

This project uses **OAuth 1.0a** — recommended by Twitter for automated bots.

## Customization

### Change posting time

Edit `.github/workflows/daily.yml`, modify the cron line:
```yaml
- cron: "42 23 * * *"   # 6:42 AM WIB (23:42 UTC)
#         M  H  D  M  DOW
```

Use https://crontab.guru to pick your time (in UTC).

### Change translation

Modify `fetch_quran.py` line with the API URL. Available English translations:
- `en.sahih` — Sahih International (default, modern)
- `en.yusufali` — Yusuf Ali (classic, poetic)
- `en.pickthall` — Pickthall

Change `editions/quran-uthmani,en.sahih` to your preference, re-run `fetch_quran.py`.

### Manually curate pool

Edit `CURATED_STANDALONE` dict in `fetch_quran.py` — add/remove specific `surah:ayah` keys.
Then regenerate:
```bash
.venv/bin/python fetch_quran.py
```

### Skip specific ayahs

Create `blacklist.json` next to the scripts:
```json
["2:1", "3:7"]
```
(Pending feature — edit `post_daily.py` to load blacklist.)

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Forbidden/403" | App permissions are Read-only — change to **Read & Write** in console.x.com |
| "Unauthorized/401" | Regenerate Access Token in console.x.com → OAuth 1.0a Keys |
| "standalone_pool.json not found" | Run `fetch_quran.py` first |
| Workflow not running | Check Actions tab enabled in GitHub repo settings |
| Already posted today | Script skips if `last_post_date` equals today (UTC) |
| `ModuleNotFoundError: No module named 'tweepy'` | Run `.venv/bin/pip install tweepy` |

## License

MIT — Quran text is public domain. Use freely.
