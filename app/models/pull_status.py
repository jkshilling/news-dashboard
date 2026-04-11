from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db import Base


class PullStatus(Base):
    __tablename__ = "pull_status"

    id = Column(Integer, primary_key=True)
    # topic_id and source_id together identify a pull run; either may be null
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=True, index=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=True, index=True)
    last_attempted_at = Column(DateTime)
    last_succeeded_at = Column(DateTime)
    items_found = Column(Integer, default=0)
    items_stored = Column(Integer, default=0)
    last_error = Column(String)
    is_error = Column(Boolean, default=False)
    synthesis_status = Column(String)  # pending | running | done | failed | n/a
    synthesis_last_run = Column(DateTime)

    __table_args__ = (
        UniqueConstraint("topic_id", "source_id", name="uix_pull_status_topic_source"),
    )

    topic = relationship("Topic", back_populates="pull_statuses")
    source = relationship("Source", back_populates="pull_statuses")
