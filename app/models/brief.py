from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import relationship

from app.db import Base


class Brief(Base):
    __tablename__ = "briefs"

    id = Column(Integer, primary_key=True)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False, unique=True)
    topline = Column(String)
    executive_summary = Column(String)
    main_themes = Column(JSON, default=list)
    what_changed = Column(String)
    emerging_angles = Column(JSON, default=list)
    consensus = Column(JSON, default=list)
    disagreement = Column(JSON, default=list)
    sentiment_summary = Column(String)
    sentiment_labels = Column(JSON, default=list)
    coverage_asymmetries = Column(JSON, default=list)
    watch_items = Column(JSON, default=list)
    narrative_frames = Column(JSON, default=list)
    generated_at = Column(DateTime, default=datetime.utcnow)
    article_count = Column(Integer, default=0)
    # Snapshot of the previous brief for change comparison; stored as JSON blob
    previous_brief_data = Column(JSON)

    topic = relationship("Topic", back_populates="brief")
