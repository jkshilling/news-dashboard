from __future__ import annotations
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.pull_status import PullStatus


def get_all(db: Session) -> list[PullStatus]:
    return db.query(PullStatus).order_by(PullStatus.last_attempted_at.desc().nullslast()).all()


def get_by_topic_source(
    db: Session, topic_id: int | None, source_id: int | None
) -> PullStatus | None:
    return (
        db.query(PullStatus)
        .filter(PullStatus.topic_id == topic_id, PullStatus.source_id == source_id)
        .first()
    )


def upsert(
    db: Session,
    topic_id: int | None,
    source_id: int | None,
    *,
    attempted: bool = True,
    succeeded: bool = False,
    items_found: int = 0,
    items_stored: int = 0,
    error: str | None = None,
    synthesis_status: str | None = None,
    synthesis_ran: bool = False,
) -> PullStatus:
    status = get_by_topic_source(db, topic_id, source_id)
    if status is None:
        status = PullStatus(topic_id=topic_id, source_id=source_id)
        db.add(status)

    now = datetime.utcnow()
    if attempted:
        status.last_attempted_at = now
    if succeeded:
        status.last_succeeded_at = now
        status.is_error = False
        status.last_error = None
    if error is not None:
        status.last_error = error
        status.is_error = True
    if items_found:
        status.items_found = items_found
    if items_stored:
        status.items_stored = items_stored
    if synthesis_status is not None:
        status.synthesis_status = synthesis_status
    if synthesis_ran:
        status.synthesis_last_run = now

    db.commit()
    db.refresh(status)
    return status
