from __future__ import annotations
"""
Status aggregation for the pull status page.
Joins pull_status records with topic and source names for display.
"""
import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.pull_status import PullStatus
from app.models.topic import Topic
from app.models.source import Source
from app.repositories import article_repository, brief_repository, status_repository

log = logging.getLogger(__name__)

# Thresholds for freshness indicators
FRESH_HOURS = 2
STALE_HOURS = 12


def get_dashboard_summary(db: Session) -> list[dict]:
    """Return per-topic status summaries for the homepage."""
    topics = db.query(Topic).filter(Topic.enabled == True).order_by(Topic.name).all()  # noqa: E712
    summaries = []

    for topic in topics:
        brief = brief_repository.get_by_topic(db, topic.id)
        article_count = article_repository.count_by_topic(db, topic.id)
        recent_count = article_repository.count_recent_by_topic(
            db, topic.id, since=datetime.utcnow() - timedelta(hours=24)
        )

        # Find latest pull status for this topic (across all sources)
        latest_pull = (
            db.query(PullStatus)
            .filter(PullStatus.topic_id == topic.id)
            .order_by(PullStatus.last_attempted_at.desc().nullslast())
            .first()
        )
        # Also check source-level statuses
        source_pull = (
            db.query(PullStatus)
            .filter(PullStatus.source_id != None, PullStatus.topic_id == None)  # noqa: E711
            .order_by(PullStatus.last_attempted_at.desc().nullslast())
            .first()
        )

        last_pull_at = None
        has_error = False
        if latest_pull:
            last_pull_at = latest_pull.last_succeeded_at or latest_pull.last_attempted_at
            has_error = latest_pull.is_error
        elif source_pull:
            last_pull_at = source_pull.last_succeeded_at

        freshness = _freshness_label(last_pull_at, has_error)
        movement = _movement_label(recent_count)

        summaries.append({
            "topic": topic,
            "brief": brief,
            "article_count": article_count,
            "recent_count": recent_count,
            "last_pull_at": last_pull_at,
            "freshness": freshness,
            "movement": movement,
            "has_error": has_error,
        })

    return summaries


def get_status_table(db: Session) -> list[dict]:
    """Return full status table rows for the status page."""
    rows = []

    # Per-source pull statuses
    sources = db.query(Source).filter(Source.active == True).order_by(Source.category_tag, Source.name).all()  # noqa: E712
    for source in sources:
        ps = status_repository.get_by_topic_source(db, topic_id=None, source_id=source.id)
        rows.append({
            "kind": "source",
            "name": source.name,
            "slug": source.slug,
            "category_tag": source.category_tag if source.category_tag else "other",
            "last_attempted_at": ps.last_attempted_at if ps else None,
            "last_succeeded_at": ps.last_succeeded_at if ps else None,
            "items_found": ps.items_found if ps else 0,
            "items_stored": ps.items_stored if ps else 0,
            "last_error": ps.last_error if ps else None,
            "is_error": ps.is_error if ps else False,
            "synthesis_status": None,
            "synthesis_last_run": None,
        })

    # Per-topic synthesis statuses
    topics = db.query(Topic).filter(Topic.enabled == True).order_by(Topic.name).all()  # noqa: E712
    for topic in topics:
        ps = status_repository.get_by_topic_source(db, topic_id=topic.id, source_id=None)
        rows.append({
            "kind": "topic",
            "name": topic.name,
            "slug": topic.slug,
            "last_attempted_at": ps.last_attempted_at if ps else None,
            "last_succeeded_at": ps.last_succeeded_at if ps else None,
            "items_found": ps.items_found if ps else 0,
            "items_stored": ps.items_stored if ps else 0,
            "last_error": ps.last_error if ps else None,
            "is_error": ps.is_error if ps else False,
            "synthesis_status": ps.synthesis_status if ps else "pending",
            "synthesis_last_run": ps.synthesis_last_run if ps else None,
        })

    return rows


def _freshness_label(last_pull_at: datetime | None, has_error: bool) -> str:
    if has_error:
        return "error"
    if last_pull_at is None:
        return "warning"
    age = datetime.utcnow() - last_pull_at
    if age < timedelta(hours=FRESH_HOURS):
        return "fresh"
    if age < timedelta(hours=STALE_HOURS):
        return "stale"
    return "warning"


def _movement_label(recent_count: int) -> str:
    if recent_count >= 20:
        return "high movement"
    if recent_count >= 5:
        return "moderate movement"
    return "low movement"
