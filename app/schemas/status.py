from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class PullStatusOut(BaseModel):
    id: int
    topic_id: Optional[int] = None
    source_id: Optional[int] = None
    last_attempted_at: Optional[datetime] = None
    last_succeeded_at: Optional[datetime] = None
    items_found: int = 0
    items_stored: int = 0
    last_error: Optional[str] = None
    is_error: bool = False
    synthesis_status: Optional[str] = None
    synthesis_last_run: Optional[datetime] = None

    model_config = {"from_attributes": True}
