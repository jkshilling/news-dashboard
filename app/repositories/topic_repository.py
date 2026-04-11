from __future__ import annotations
from sqlalchemy.orm import Session

from app.models.topic import Topic


def get_all(db: Session, enabled_only: bool = True) -> list[Topic]:
    q = db.query(Topic)
    if enabled_only:
        q = q.filter(Topic.enabled == True)  # noqa: E712
    return q.order_by(Topic.name).all()


def get_by_slug(db: Session, slug: str) -> Topic | None:
    return db.query(Topic).filter(Topic.slug == slug).first()


def get_by_id(db: Session, topic_id: int) -> Topic | None:
    return db.query(Topic).filter(Topic.id == topic_id).first()


def upsert_from_config(db: Session, data: dict) -> Topic:
    topic = db.query(Topic).filter(Topic.slug == data["slug"]).first()
    if topic is None:
        topic = Topic()
        db.add(topic)
    for k, v in data.items():
        setattr(topic, k, v)
    db.commit()
    db.refresh(topic)
    return topic
