"""Telegram bot that sends back the current Instagram stories of a public account."""

from __future__ import annotations

import asyncio
import logging
import os
import time

import httpx
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from ig import InstagramClient, StoryError
from utils import parse_allowed_ids, parse_username

load_dotenv()

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger("insta-story-bot")

COOLDOWN_SECONDS = int(os.getenv("COOLDOWN_SECONDS", "20"))
MAX_STORIES = int(os.getenv("MAX_STORIES", "30"))

HELP_TEXT = (
    "Send me an Instagram username (like @natgeo) or a profile link and I'll send "
    "back that account's current stories.\n\n"
    "Only public accounts work. Please respect people's content and Instagram's terms."
)


def is_allowed(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    allowed: set[int] = context.application.bot_data["allowed_ids"]
    return not allowed or user_id in allowed


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message:
        await update.effective_message.reply_text("Hi! " + HELP_TEXT)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message:
        await update.effective_message.reply_text(HELP_TEXT)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    if message is None or user is None:
        return

    if not is_allowed(context, user.id):
        await message.reply_text("Sorry, this bot is private.")
        return

    username = parse_username(message.text)
    if username is None:
        await message.reply_text(
            "I couldn't find a username there. Send something like @natgeo."
        )
        return

    # Per-user cooldown keeps the bot's Instagram account from being rate-limited.
    cooldowns: dict[int, float] = context.application.bot_data["cooldowns"]
    now = time.monotonic()
    wait = cooldowns.get(user.id, 0.0) + COOLDOWN_SECONDS - now
    if wait > 0:
        await message.reply_text(f"Please wait {int(wait) + 1}s before the next request.")
        return
    cooldowns[user.id] = now

    status = await message.reply_text(f"Looking for @{username}'s stories...")

    ig: InstagramClient = context.application.bot_data["ig"]
    lock: asyncio.Lock = context.application.bot_data["lock"]
    try:
        # Instaloader is blocking and not thread-safe: one request at a time, off the event loop.
        async with lock:
            stories = await asyncio.to_thread(ig.fetch_stories, username, MAX_STORIES)
    except StoryError as ex:
        await status.edit_text(str(ex))
        return
    except Exception:
        logger.exception("Unexpected error while fetching @%s", username)
        await status.edit_text("Something went wrong. Please try again later.")
        return

    await status.edit_text(f"Found {len(stories)} stories. Sending...")

    sent = 0
    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as http:
        for story in stories:
            try:
                response = await http.get(story.url)
                response.raise_for_status()
                caption = f"@{username} - {story.taken_at:%Y-%m-%d %H:%M} UTC"
                if story.is_video:
                    await message.reply_video(
                        video=response.content,
                        caption=caption,
                        supports_streaming=True,
                        write_timeout=120,
                    )
                else:
                    await message.reply_photo(
                        photo=response.content,
                        caption=caption,
                        write_timeout=60,
                    )
                sent += 1
            except Exception:
                logger.exception("Could not send a story from @%s", username)

    await status.edit_text(f"Done. Sent {sent} of {len(stories)} stories.")


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Unhandled error", exc_info=context.error)


def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    ig_username = os.getenv("IG_USERNAME")
    if not token or not ig_username:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN and IG_USERNAME (see .env.example).")

    ig = InstagramClient(
        username=ig_username,
        session_file=os.getenv("IG_SESSION_FILE") or None,
        password=os.getenv("IG_PASSWORD") or None,
    )
    try:
        ig.login()
    except Exception as ex:
        raise SystemExit(f"Instagram login failed: {ex}") from ex

    app = Application.builder().token(token).concurrent_updates(True).build()
    app.bot_data.update(
        ig=ig,
        lock=asyncio.Lock(),
        cooldowns={},
        allowed_ids=parse_allowed_ids(os.getenv("ALLOWED_USER_IDS")),
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, handle_text
        )
    )
    app.add_error_handler(on_error)

    logger.info("Bot is running.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
