from __future__ import annotations
from typing import Optional
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

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


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
    source_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    topic = topic_repository.get_by_slug(db, slug)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    brief = brief_repository.get_by_topic(db, topic.id)
    articles = article_repository.get_by_topic(
        db, topic.id, limit=50, sort=sort, source_id=source_id
    )
    sources = source_repository.get_all(db, active_only=False)

    return templates.TemplateResponse(request, "topic_detail.html", {
        "topic": topic,
        "brief": brief,
        "articles": articles,
        "sources": sources,
        "current_sort": sort,
        "current_source_id": source_id,
    })


@router.get("/status", response_class=HTMLResponse)
async def status_page(request: Request, db: Session = Depends(get_db)):
    rows = status_service.get_status_table(db)
    return templates.TemplateResponse(request, "status.html", {
        "rows": rows,
    })
