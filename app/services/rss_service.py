from __future__ import annotations
"""
RSS ingestion service. Fetches and normalises entries from a feed URL.
Returns a list of raw article dicts before topic matching.
"""
import logging
from datetime import datetime, timezone

import feedparser
import httpx

from app.config import settings
from app.models.source import Source

log = logging.getLogger(__name__)


def fetch_feed(source: Source) -> list[dict]:
    """Fetch an RSS/Atom feed and return normalised article dicts."""
    if not source.feed_url:
        log.warning("Source %s has no feed_url", source.slug)
        return []

    try:
        resp = httpx.get(
            source.feed_url,
            timeout=settings.REQUEST_TIMEOUT_SECONDS,
            headers={"User-Agent": settings.USER_AGENT},
            follow_redirects=True,
        )
        resp.raise_for_status()
        raw = resp.text
    except Exception as exc:
        log.error("RSS fetch failed for %s: %s", source.slug, exc)
        raise

    feed = feedparser.parse(raw)

    articles = []
    for entry in feed.entries:
        article = _normalise_entry(entry, source)
        if article:
            articles.append(article)

    log.info("RSS %s: %d entries parsed", source.slug, len(articles))
    return articles


def _normalise_entry(entry, source: Source) -> dict | None:
    url = entry.get("link") or ""
    if not url:
        return None

    headline = entry.get("title") or ""
    if not headline:
        return None

    # Best-effort snippet extraction
    snippet = ""
    if hasattr(entry, "summary"):
        snippet = _strip_html(entry.summary or "")
    elif hasattr(entry, "description"):
        snippet = _strip_html(entry.description or "")
    snippet = snippet[:500]

    published_at = _parse_date(entry)

    return {
        "headline": headline.strip(),
        "snippet": snippet.strip(),
        "url": url.strip(),
        "published_at": published_at,
        "source_slug": source.slug,
        "source_id": source.id,
    }


def _parse_date(entry) -> datetime | None:
    ts = entry.get("published_parsed") or entry.get("updated_parsed")
    if ts:
        try:
            return datetime(*ts[:6], tzinfo=timezone.utc).replace(tzinfo=None)
        except Exception:
            pass
    return None


def _strip_html(text: str) -> str:
    """Very lightweight HTML tag stripping without a full parser."""
    import re
    return re.sub(r"<[^>]+>", " ", text).strip()
