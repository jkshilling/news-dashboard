from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ArticleOut(BaseModel):
    id: int
    topic_id: int
    source_id: int
    headline: str
    snippet: Optional[str] = None
    url: str
    published_at: Optional[datetime] = None
    fetched_at: Optional[datetime] = None
    relevance_score: float = 0.0
    matched_terms: list[str] = []
    match_reason: Optional[str] = None

    model_config = {"from_attributes": True}
