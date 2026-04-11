from __future__ import annotations
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, field_validator


VALID_FRAME_STATUSES = {"dominant", "emerging", "fading", "contested"}
VALID_SENTIMENT_LABELS = {
    "alarmed", "celebratory", "skeptical", "adversarial",
    "procedural", "speculative", "condemnatory", "neutral",
}


class NarrativeFrame(BaseModel):
    label: str
    status: str
    evidence: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in VALID_FRAME_STATUSES:
            return "emerging"
        return v


class BriefSchema(BaseModel):
    topline: str = ""
    executive_summary: str = ""
    main_themes: list[str] = []
    what_changed: str = ""
    emerging_angles: list[str] = []
    consensus: list[str] = []
    disagreement: list[str] = []
    sentiment_summary: str = ""
    sentiment_labels: list[str] = []
    coverage_asymmetries: list[str] = []
    watch_items: list[str] = []
    narrative_frames: list[NarrativeFrame] = []
    generated_at: Optional[datetime] = None

    @field_validator("sentiment_labels")
    @classmethod
    def validate_sentiment_labels(cls, labels: list[str]) -> list[str]:
        return [lbl if lbl in VALID_SENTIMENT_LABELS else "neutral" for lbl in labels]

    @field_validator("narrative_frames", mode="before")
    @classmethod
    def coerce_frames(cls, frames: Any) -> list[Any]:
        if not isinstance(frames, list):
            return []
        return frames


class BriefOut(BaseModel):
    id: int
    topic_id: int
    topline: Optional[str] = None
    executive_summary: Optional[str] = None
    main_themes: list[str] = []
    what_changed: Optional[str] = None
    emerging_angles: list[str] = []
    consensus: list[str] = []
    disagreement: list[str] = []
    sentiment_summary: Optional[str] = None
    sentiment_labels: list[str] = []
    coverage_asymmetries: list[str] = []
    watch_items: list[str] = []
    narrative_frames: list[Any] = []
    generated_at: Optional[datetime] = None
    article_count: int = 0

    model_config = {"from_attributes": True}
