from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db import get_db
from app.repositories import (
    article_repository,
    brief_repository,
    source_repository,
    topic_repository,
)
from app.services import status_service

ALASKA = ZoneInfo("America/Anchorage")

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def _to_akdt(dt: datetime | None, fmt: str = "%m-%d %H:%M") -> str:
    if dt is None:
        return "—"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(ALASKA).strftime(fmt)


templates.env.filters["akdt"] = _to_akdt


@router.get("/", response_class=HTMLResponse)
async def index(request: Request, db: Session = Depends(get_db)):
    summaries = status_service.get_dashboard_summary(db)
    return templates.TemplateResponse(request, "index.html", {
        "summaries": summaries,
    })


@router.get("/topic/{slug}", response_class=HTMLResponse)
async def topic_detail(
    request: Request,
    slug: str,
    sort: str = "newest",
    source_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    topic = topic_repository.get_by_slug(db, slug)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    source_id_int = int(source_id) if source_id and source_id.isdigit() else None

    brief = brief_repository.get_by_topic(db, topic.id)
    articles = article_repository.get_by_topic(
        db, topic.id, limit=50, sort=sort, source_id=source_id_int
    )
    sources = source_repository.get_all(db, active_only=True)

    return templates.TemplateResponse(request, "topic_detail.html", {
        "topic": topic,
        "brief": brief,
        "articles": articles,
        "sources": sources,
        "current_sort": sort,
        "current_source_id": source_id_int,
    })


CATEGORY_ORDER = ["statewide", "regional", "industry", "opinion", "national", "other"]
CATEGORY_LABELS = {
    "statewide": "Statewide",
    "regional": "Regional",
    "industry": "Industry",
    "opinion": "Opinion & Commentary",
    "national": "National",
    "other": "Other",
}

@router.get("/status", response_class=HTMLResponse)
async def status_page(request: Request, db: Session = Depends(get_db)):
    rows = status_service.get_status_table(db)
    source_rows = [r for r in rows if r["kind"] == "source"]
    topic_rows = [r for r in rows if r["kind"] == "topic"]
    # Normalize unknown category_tags to "other"
    known = set(CATEGORY_ORDER)
    for r in source_rows:
        if r["category_tag"] not in known:
            r["category_tag"] = "other"
    source_groups = []
    for cat_key in CATEGORY_ORDER:
        group = [r for r in source_rows if r["category_tag"] == cat_key]
        if group:
            source_groups.append({"label": CATEGORY_LABELS[cat_key], "rows": group})
    return templates.TemplateResponse(request, "status.html", {
        "source_groups": source_groups,
        "topic_rows": topic_rows,
    })
