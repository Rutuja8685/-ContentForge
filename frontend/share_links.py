"""URL builders for user-confirmed social sharing."""

from urllib.parse import quote

LINKEDIN_SHARE_BASE = "https://www.linkedin.com/feed/?shareActive=true&text="
X_SHARE_BASE = "https://x.com/intent/post?text="
LINKEDIN_URL_LIMIT = 7000


def build_linkedin_share_url(text: str) -> str:
    """Build a UTF-8 encoded LinkedIn share URL from editable post text."""
    return LINKEDIN_SHARE_BASE + quote(text, safe="")


def build_x_share_url(tweet_text: str) -> str:
    """Build a UTF-8 encoded X intent URL from one editable tweet."""
    return X_SHARE_BASE + quote(tweet_text, safe="")
