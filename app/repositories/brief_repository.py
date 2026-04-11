from __future__ import annotations
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.brief import Brief
from app.schemas.brief import BriefSchema


def get_by_topic(db: Session, topic_id: int) -> Brief | None:
    return db.query(Brief).filter(Brief.topic_id == topic_id).first()


def upsert(db: Session, topic_id: int, schema: BriefSchema, article_count: int) -> Brief:
    brief = db.query(Brief).filter(Brief.topic_id == topic_id).first()
    if brief is None:
        brief = Brief(topic_id=topic_id)
        db.add(brief)
    else:
        # Archive the current brief as previous_brief_data before overwriting
        brief.previous_brief_data = {
            "topline": brief.topline,
            "executive_summary": brief.executive_summary,
            "main_themes": brief.main_themes,
            "what_changed": brief.what_changed,
            "emerging_angles": brief.emerging_angles,
            "consensus": brief.consensus,
            "disagreement": brief.disagreement,
            "sentiment_summary": brief.sentiment_summary,
            "sentiment_labels": brief.sentiment_labels,
            "coverage_asymmetries": brief.coverage_asymmetries,
            "watch_items": brief.watch_items,
            "narrative_frames": brief.narrative_frames,
            "generated_at": brief.generated_at.isoformat() if brief.generated_at else None,
            "article_count": brief.article_count,
        }

    brief.topline = schema.topline
    brief.executive_summary = schema.executive_summary
    brief.main_themes = schema.main_themes
    brief.what_changed = schema.what_changed
    brief.emerging_angles = schema.emerging_angles
    brief.consensus = schema.consensus
    brief.disagreement = schema.disagreement
    brief.sentiment_summary = schema.sentiment_summary
    brief.sentiment_labels = schema.sentiment_labels
    brief.coverage_asymmetries = schema.coverage_asymmetries
    brief.watch_items = schema.watch_items
    brief.narrative_frames = [f.model_dump() for f in schema.narrative_frames]
    brief.generated_at = schema.generated_at or datetime.utcnow()
    brief.article_count = article_count

    db.commit()
    db.refresh(brief)
    return brief
