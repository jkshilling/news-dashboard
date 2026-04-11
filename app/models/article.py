from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import relationship

from app.db import Base


class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False, index=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False)
    headline = Column(String, nullable=False)
    snippet = Column(String)
    body_text = Column(String)  # extracted full text, populated only when needed for synthesis
    url = Column(String, nullable=False)
    canonical_url = Column(String, index=True)
    published_at = Column(DateTime)
    fetched_at = Column(DateTime, default=datetime.utcnow)
    relevance_score = Column(Float, default=0.0)
    matched_terms = Column(JSON, default=list)
    match_reason = Column(String)
    excluded_term_hits = Column(JSON, default=list)
    is_synthesis_candidate = Column(Boolean, default=True)

    topic = relationship("Topic", back_populates="articles")
    source = relationship("Source", back_populates="articles")
