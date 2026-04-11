from sqlalchemy import Boolean, Column, Integer, JSON, String
from sqlalchemy.orm import relationship

from app.db import Base


class Topic(Base):
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, nullable=False, index=True)
    description = Column(String)
    query_terms = Column(JSON, default=list)
    include_terms = Column(JSON, default=list)
    exclude_terms = Column(JSON, default=list)
    # Empty list = all sources; non-empty = only these source slugs
    source_scope_override = Column(JSON, default=list)
    enabled = Column(Boolean, default=True)

    articles = relationship("Article", back_populates="topic", cascade="all, delete-orphan")
    brief = relationship("Brief", back_populates="topic", uselist=False, cascade="all, delete-orphan")
    pull_statuses = relationship("PullStatus", back_populates="topic", cascade="all, delete-orphan")
