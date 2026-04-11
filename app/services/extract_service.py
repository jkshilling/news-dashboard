from __future__ import annotations
"""
Article text extraction. Tries trafilatura first, falls back to
a BeautifulSoup paragraph scan. Used only when synthesis needs
fuller body text than the snippet provides.
"""
import logging

import httpx

from app.config import settings

log = logging.getLogger(__name__)


def extract_text(url: str) -> str | None:
    """Fetch a URL and return cleaned body text, or None on failure."""
    try:
        resp = httpx.get(
            url,
            timeout=settings.REQUEST_TIMEOUT_SECONDS,
            headers={"User-Agent": settings.USER_AGENT},
            follow_redirects=True,
        )
        resp.raise_for_status()
        html = resp.text
    except Exception as exc:
        log.warning("extract_text fetch failed for %s: %s", url, exc)
        return None

    # Try trafilatura first — highest quality extraction
    try:
        import trafilatura

        text = trafilatura.extract(html, include_comments=False, include_tables=False)
        if text and len(text) > 100:
            return text[:4000]
    except Exception as exc:
        log.debug("trafilatura failed for %s: %s", url, exc)

    # Fallback: collect <p> tags via BeautifulSoup
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        paragraphs = [p.get_text(separator=" ").strip() for p in soup.find_all("p")]
        text = " ".join(p for p in paragraphs if len(p) > 40)
        if text:
            return text[:4000]
    except Exception as exc:
        log.debug("BeautifulSoup fallback failed for %s: %s", url, exc)

    return None
