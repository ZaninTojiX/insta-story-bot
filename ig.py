"""Thin wrapper around Instaloader that fetches the current stories of a public profile."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

import instaloader
from instaloader.exceptions import (
    InstaloaderException,
    LoginRequiredException,
    ProfileNotExistsException,
    TooManyRequestsException,
)

logger = logging.getLogger(__name__)


class StoryError(Exception):
    """Base error. The message is written for the end user and is safe to show in Telegram."""


class ProfileNotFound(StoryError):
    pass


class PrivateProfile(StoryError):
    pass


class NoActiveStories(StoryError):
    pass


class RateLimited(StoryError):
    pass


class InstagramUnavailable(StoryError):
    pass


@dataclass(frozen=True)
class StoryMedia:
    url: str
    is_video: bool
    taken_at: datetime


class InstagramClient:
    """Logged-in Instagram session used to read stories.

    Instagram only shows stories to logged-in accounts, so the bot needs one.
    Use a dedicated account, not your personal one.
    """

    def __init__(
        self,
        username: str,
        session_file: str | None = None,
        password: str | None = None,
    ) -> None:
        self.username = username
        self.session_file = session_file
        self.password = password
        self.loader = instaloader.Instaloader(
            download_pictures=False,
            download_videos=False,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            compress_json=False,
            quiet=True,
        )

    def login(self) -> None:
        """Log in at startup. Raises an exception with a clear message for the bot owner."""
        if self.session_file:
            self.loader.load_session_from_file(self.username, self.session_file)
        elif self.password:
            self.loader.login(self.username, self.password)
        else:
            raise RuntimeError("Set IG_SESSION_FILE (recommended) or IG_PASSWORD.")

        if self.loader.test_login() is None:
            raise RuntimeError(
                "Instagram session is not valid. Log in again and refresh the session file."
            )
        logger.info("Logged in to Instagram as %s", self.username)

    def fetch_stories(self, target: str, limit: int = 30) -> list[StoryMedia]:
        """Blocking call, run it in a thread. Raises StoryError subclasses.

        Private profiles are refused on purpose, even if the bot's account follows them.
        """
        items: list[StoryMedia] = []
        try:
            profile = instaloader.Profile.from_username(self.loader.context, target)
            if profile.is_private:
                raise PrivateProfile(
                    f"@{target} is a private account, so I can't download its stories."
                )

            for story in self.loader.get_stories(userids=[profile.userid]):
                for item in story.get_items():
                    url = item.video_url if item.is_video else item.url
                    if url:
                        items.append(
                            StoryMedia(
                                url=url,
                                is_video=bool(item.is_video),
                                taken_at=item.date_utc,
                            )
                        )
                    if len(items) >= limit:
                        break
                if len(items) >= limit:
                    break
        except ProfileNotExistsException as ex:
            raise ProfileNotFound(
                f"I couldn't find an Instagram account named @{target}."
            ) from ex
        except TooManyRequestsException as ex:
            raise RateLimited(
                "Instagram is rate-limiting the bot right now. Please try again in a few minutes."
            ) from ex
        except LoginRequiredException as ex:
            logger.error("Instagram session is no longer valid: %s", ex)
            raise InstagramUnavailable(
                "The bot's Instagram login has expired. The owner needs to log in again."
            ) from ex
        except InstaloaderException as ex:
            logger.warning("Instagram request failed for @%s: %s", target, ex)
            raise InstagramUnavailable(
                "Instagram didn't respond properly. Please try again later."
            ) from ex

        if not items:
            raise NoActiveStories(f"@{target} has no active stories right now.")

        items.sort(key=lambda media: media.taken_at)
        return items
