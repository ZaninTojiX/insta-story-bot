"""Small helpers with no third-party dependencies, so they are easy to test."""

from __future__ import annotations

import re

# Instagram usernames: 1-30 characters, letters, digits, periods and underscores.
_USERNAME = r"[A-Za-z0-9._]{1,30}"

_URL_RE = re.compile(
    rf"(?<![\w.-])(?:https?://)?(?:www\.)?instagram\.com/(?:stories/)?"
    rf"(?P<name>{_USERNAME})(?:[/?#]|$)",
    re.IGNORECASE,
)
_PLAIN_RE = re.compile(rf"^@?(?P<name>{_USERNAME})$")

# First path segments on instagram.com that are not profile names.
_RESERVED = {
    "p", "reel", "reels", "tv", "explore", "accounts", "stories",
    "direct", "about", "web", "s", "highlights",
}


def parse_username(text: str | None) -> str | None:
    """Return a lowercase Instagram username from '@name', 'name' or a profile/story link.

    Returns None when the text does not look like a profile reference
    (for example a post or reel link, or a normal sentence).
    """
    text = (text or "").strip()
    if not text:
        return None

    match = _URL_RE.search(text) or _PLAIN_RE.match(text)
    if match is None:
        return None

    name = match.group("name").lower()
    if name in _RESERVED:
        return None
    return name


def parse_allowed_ids(value: str | None) -> set[int]:
    """Parse a comma or space separated list of Telegram user IDs. Invalid parts are ignored."""
    ids: set[int] = set()
    for part in re.split(r"[,\s]+", value or ""):
        if part.lstrip("-").isdigit():
            ids.add(int(part))
    return ids
