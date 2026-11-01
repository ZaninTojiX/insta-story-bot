# insta-story-bot

A Telegram bot that sends back the current Instagram stories of a **public** account.
Send it `@username` or a profile link in a private chat and it replies with the photos and videos.

## Read this first

- Instagram only shows stories to logged-in accounts, so the bot needs an Instagram login.
  **Use a dedicated account, not your personal one.** Automated access can get an account
  restricted or banned, and it may go against Instagram's terms of use. You use this at your own risk.
- Private accounts are refused on purpose, even if the bot's account follows them.
- Only download content you have the right to use, and respect the people who posted it.
- The session file is a login credential. Never commit it or share it.

## Setup

1. Create a bot with [@BotFather](https://t.me/BotFather) and copy the token.
2. Install and log in with Instaloader on your own computer to create a session file:

   ```bash
   pip install instaloader
   instaloader --login YOUR_BOT_IG_USERNAME
   ```

   Instaloader then stores `session-YOUR_BOT_IG_USERNAME` in its config folder
   (usually `~/.config/instaloader/` on Linux and macOS).
3. Copy `.env.example` to `.env` and fill it in. Set `IG_SESSION_FILE` to the full path of
   the session file (or use `IG_PASSWORD` instead, which is more likely to hit Instagram checkpoints).
4. Install and run:

   ```bash
   pip install -r requirements.txt
   python bot.py
   ```

## Configuration

| Variable | Required | Meaning |
| --- | --- | --- |
| `TELEGRAM_BOT_TOKEN` | yes | Token from @BotFather |
| `IG_USERNAME` | yes | Instagram account the bot logs in with |
| `IG_SESSION_FILE` | one of these | Path to the Instaloader session file |
| `IG_PASSWORD` | one of these | Password login (alternative to the session file) |
| `ALLOWED_USER_IDS` | no | Comma-separated Telegram user IDs; empty means everyone |
| `COOLDOWN_SECONDS` | no | Wait between requests per user (default 20) |
| `MAX_STORIES` | no | Maximum stories sent per request (default 30) |

## Run with Docker

```bash
docker build -t insta-story-bot .
docker run --env-file .env -v /path/to/session-file:/app/session:ro insta-story-bot
```

With that mount, set `IG_SESSION_FILE=/app/session`. On a host like Render, run it as a
background worker and add the session file as a secret file.

## Tests

```bash
python -m unittest
```

The tests cover the username and link parsing. The Instagram and Telegram parts need real accounts, so
check those by running the bot.
