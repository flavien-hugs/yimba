from __future__ import annotations

from enum import StrEnum


class SourceKind(StrEnum):
    """Where a mention comes from. Shared vocabulary of watches, collection and mentions."""

    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    TWITTER = "twitter"
    YOUTUBE = "youtube"
    GOOGLE = "google"
    NEWS = "news"
