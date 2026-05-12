from __future__ import annotations

import logging
import re

import requests
from bs4 import BeautifulSoup

from .models import SearchResult

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (compatible; SpeakingGigAgent/1.0; "
    "+https://github.com/your-org/speaking-gig-agent)"
)


def fetch_page_text(url: str, timeout: int = 20, max_chars: int = 16000) -> str:
    """Fetch and clean visible page text. Returns an empty string on failure."""
    try:
        response = requests.get(
            url,
            timeout=timeout,
            headers={"User-Agent": USER_AGENT},
            allow_redirects=True,
        )
        response.raise_for_status()
    except Exception as exc:
        logger.warning("Failed to fetch %s: %s", url, exc)
        return ""

    content_type = response.headers.get("content-type", "").lower()
    if "text/html" not in content_type and "application/xhtml" not in content_type:
        logger.info("Skipping non-HTML page: %s (%s)", url, content_type)
        return ""

    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "header", "footer", "nav"]):
        tag.decompose()

    text = soup.get_text(separator=" ")
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars]


def build_candidate_context(result: SearchResult, page_text: str) -> str:
    return f"""Title: {result.title}
URL: {result.url}
Source query: {result.source_query}
Search snippet: {result.snippet}

Page text:
{page_text}
"""
