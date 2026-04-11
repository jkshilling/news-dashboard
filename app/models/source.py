from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy.orm import relationship

from app.db import Base


class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, nullable=False, index=True)
    homepage = Column(String)
    source_type = Column(String, nullable=False)  # rss | api | scrape
    feed_url = Column(String)
    listing_url = Column(String)
    article_url_pattern = Column(String)
    category_tag = Column(String)
    bias_tag = Column(String)
    fetch_priority = Column(Integer, default=5)
    active = Column(Boolean, default=True)
    parser_strategy = Column(String, default="default")

    articles = relationship("Article", back_populates="source")
    pull_statuses = relationship("PullStatus", back_populates="source", cascade="all, delete-orphan")
