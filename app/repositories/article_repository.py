from __future__ import annotations
from datetime import datetime

from sqlalchemy.orm import Session

from app.config import settings
from app.models.article import Article


def get_by_topic(
    db: Session,
    topic_id: int,
    limit: int = 50,
    offset: int = 0,
    sort: str = "newest",
    source_id: int | None = None,
) -> list[Article]:
    q = db.query(Article).filter(Article.topic_id == topic_id)
    if source_id is not None:
        q = q.filter(Article.source_id == source_id)
    if sort == "oldest":
        q = q.order_by(Article.published_at.asc().nullslast())
    elif sort == "score":
        q = q.order_by(Article.relevance_score.desc())
    else:
        q = q.order_by(Article.published_at.desc().nullslast())
    return q.offset(offset).limit(limit).all()


def count_by_topic(db: Session, topic_id: int) -> int:
    return db.query(Article).filter(Article.topic_id == topic_id).count()


def count_recent_by_topic(db: Session, topic_id: int, since: datetime) -> int:
    return (
        db.query(Article)
        .filter(Article.topic_id == topic_id, Article.fetched_at >= since)
        .count()
    )


def get_synthesis_candidates(db: Session, topic_id: int, limit: int = 60) -> list[Article]:
    return (
        db.query(Article)
        .filter(Article.topic_id == topic_id, Article.is_synthesis_candidate == True)  # noqa: E712
        .order_by(Article.relevance_score.desc(), Article.published_at.desc().nullslast())
        .limit(limit)
        .all()
    )


def url_exists(db: Session, canonical_url: str, topic_id: int) -> bool:
    return (
        db.query(Article)
        .filter(Article.canonical_url == canonical_url, Article.topic_id == topic_id)
        .first()
    ) is not None


def save(db: Session, article: Article) -> Article:
    db.add(article)
    db.commit()
    db.refresh(article)
    return article


def apply_retention(db: Session, topic_id: int) -> int:
    """Delete oldest articles beyond MAX_ARTICLES_PER_TOPIC. Returns count deleted."""
    max_keep = settings.MAX_ARTICLES_PER_TOPIC
    total = count_by_topic(db, topic_id)
    if total <= max_keep:
        return 0
    excess = total - max_keep
    oldest_ids = (
        db.query(Article.id)
        .filter(Article.topic_id == topic_id)
        .order_by(Article.fetched_at.asc().nullslast())
        .limit(excess)
        .all()
    )
    ids = [row[0] for row in oldest_ids]
    db.query(Article).filter(Article.id.in_(ids)).delete(synchronize_session=False)
    db.commit()
    return len(ids)
