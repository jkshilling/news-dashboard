from __future__ import annotations
from typing import Optional
from pydantic import BaseModel


class TopicOut(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str] = None
    query_terms: list[str] = []
    include_terms: list[str] = []
    exclude_terms: list[str] = []
    enabled: bool = True

    model_config = {"from_attributes": True}
