from __future__ import annotations
"""
Ingestion pipeline orchestrator.

Preference order per source:
  1. RSS (if feed_url set)
  2. scrape listing page (if listing_url set)
  3. scrape article detail (for body extraction — deferred to synthesis time)
"""
import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.article import Article
from app.repositories import article_repository, source_repository, status_repository, topic_repository
from app.services import dedupe_service, rss_service, scrape_service, topic_matcher

log = logging.getLogger(__name__)


def run_collection(db: Session) -> dict:
    """Run one full collection pass across all active sources and enabled topics."""
    sources = source_repository.get_all(db, active_only=True)
    topics = topic_repository.get_all(db, enabled_only=True)

    total_found = 0
    total_stored = 0
    errors = []

    for source in sorted(sources, key=lambda s: s.fetch_priority):
        log.info("Collecting from source: %s (%s)", source.slug, source.source_type)
        found, stored, error = _collect_source(db, source, topics)
        total_found += found
        total_stored += stored
        if error:
            errors.append(f"{source.slug}: {error}")

    log.info("Collection done — found=%d stored=%d errors=%d", total_found, total_stored, len(errors))
    return {"found": total_found, "stored": total_stored, "errors": errors}


def _collect_source(db: Session, source, topics: list) -> tuple[int, int, str | None]:
    raw_articles: list[dict] = []
    error: str | None = None

    try:
        if source.source_type == "rss" and source.feed_url:
            raw_articles = rss_service.fetch_feed(source)
        elif source.source_type in ("scrape", "api") and source.listing_url:
            raw_articles = scrape_service.fetch_listing(source)
        else:
            log.warning("Source %s has no usable fetch strategy — skipping", source.slug)
            return 0, 0, "no fetch strategy configured"
    except Exception as exc:
        error = str(exc)[:500]
        status_repository.upsert(
            db,
            topic_id=None,
            source_id=source.id,
            attempted=True,
            succeeded=False,
            error=error,
        )
        return 0, 0, error

    found = len(raw_articles)
    stored = 0

    for raw in raw_articles:
        for topic in topics:
            result = topic_matcher.match_article_to_topic(
                headline=raw.get("headline", ""),
                snippet=raw.get("snippet", ""),
                body=raw.get("body_text", ""),
                topic=topic,
                source_slug=source.slug,
            )
            if not result["matches"]:
                continue

            # Skip if we already have this canonical URL for this topic
            c_url = dedupe_service.canonical_url(raw["url"])
            if article_repository.url_exists(db, c_url, topic.id):
                continue

            article = Article(
                topic_id=topic.id,
                source_id=source.id,
                headline=raw["headline"],
                snippet=raw.get("snippet", ""),
                url=raw["url"],
                canonical_url=c_url,
                published_at=raw.get("published_at"),
                fetched_at=datetime.utcnow(),
                relevance_score=result["relevance_score"],
                matched_terms=result["matched_terms"],
                match_reason=result["match_reason"],
                excluded_term_hits=result["excluded_term_hits"],
                is_synthesis_candidate=True,
            )
            article_repository.save(db, article)
            stored += 1

    # Enforce retention for each topic
    for topic in topics:
        article_repository.apply_retention(db, topic.id)

    status_repository.upsert(
        db,
        topic_id=None,
        source_id=source.id,
        attempted=True,
        succeeded=True,
        items_found=found,
        items_stored=stored,
    )

    log.info("  %s: found=%d stored=%d", source.slug, found, stored)
    return found, stored, None
