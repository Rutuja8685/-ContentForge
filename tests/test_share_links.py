"""Tests for UTF-8 encoded social share URLs."""

from urllib.parse import unquote

from frontend.share_links import (
    build_linkedin_share_url,
    build_x_share_url,
)


def test_linkedin_share_url_encodes_special_characters_newlines_and_marathi():
    text = "नमस्कार! #नवीन & उपयोगी\nदुसरी ओळ"

    url = build_linkedin_share_url(text)

    assert url.startswith(
        "https://www.linkedin.com/feed/?shareActive=true&text="
    )
    assert unquote(url.split("&text=", maxsplit=1)[1]) == text
    assert "%23" in url
    assert "%26" in url
    assert "%0A" in url


def test_x_share_url_encodes_special_characters_newlines_and_marathi():
    tweet = "नमस्कार #Marathi & X\nदुसरी ओळ"

    url = build_x_share_url(tweet)

    assert url.startswith("https://x.com/intent/post?text=")
    assert unquote(url.split("?text=", maxsplit=1)[1]) == tweet
    assert "%23" in url
    assert "%26" in url
    assert "%0A" in url
