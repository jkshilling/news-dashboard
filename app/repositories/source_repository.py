from __future__ import annotations
from sqlalchemy.orm import Session

from app.models.source import Source


def get_all(db: Session, active_only: bool = True) -> list[Source]:
    q = db.query(Source)
    if active_only:
        q = q.filter(Source.active == True)  # noqa: E712
    return q.order_by(Source.fetch_priority, Source.name).all()


def get_by_slug(db: Session, slug: str) -> Source | None:
    return db.query(Source).filter(Source.slug == slug).first()


def get_by_id(db: Session, source_id: int) -> Source | None:
    return db.query(Source).filter(Source.id == source_id).first()


def upsert_from_config(db: Session, data: dict) -> Source:
    source = db.query(Source).filter(Source.slug == data["slug"]).first()
    if source is None:
        source = Source()
        db.add(source)
    for k, v in data.items():
        setattr(source, k, v)
    db.commit()
    db.refresh(source)
    return source
