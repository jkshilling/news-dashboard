from __future__ import annotations
"""
Scrape-based article discovery for sources without RSS feeds.
Fetches a listing page and extracts article URLs + headlines.
"""
import logging
import re

import httpx
from bs4 import BeautifulSoup

from app.config import settings
from app.models.source import Source

log = logging.getLogger(__name__)


def fetch_listing(source: Source) -> list[dict]:
    """Scrape a listing page and return candidate article dicts."""
    if not source.listing_url:
        log.warning("Source %s has no listing_url", source.slug)
        return []

    try:
        resp = httpx.get(
            source.listing_url,
            timeout=settings.REQUEST_TIMEOUT_SECONDS,
            headers={"User-Agent": settings.USER_AGENT},
            follow_redirects=True,
        )
        resp.raise_for_status()
    except Exception as exc:
        log.error("Scrape fetch failed for %s: %s", source.slug, exc)
        raise

    soup = BeautifulSoup(resp.text, "lxml")
    articles = []

    pattern = re.compile(source.article_url_pattern) if source.article_url_pattern else None

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].strip()
        if not href.startswith("http"):
            base = source.homepage.rstrip("/") if source.homepage else ""
            href = base + href if href.startswith("/") else None
        if not href:
            continue
        if pattern and not pattern.search(href):
            continue

        headline = a_tag.get_text(separator=" ").strip()
        headline = re.sub(r"\s+", " ", headline)
        if len(headline) < 10:
            continue

        articles.append({
            "headline": headline[:300],
            "snippet": "",
            "url": href,
            "published_at": None,
            "source_slug": source.slug,
            "source_id": source.id,
        })

    # Deduplicate by URL within this batch
    seen = set()
    unique = []
    for a in articles:
        if a["url"] not in seen:
            seen.add(a["url"])
            unique.append(a)

    log.info("Scrape %s: %d candidates found", source.slug, len(unique))
    return unique
