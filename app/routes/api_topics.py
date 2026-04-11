from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.repositories import article_repository, brief_repository, topic_repository
from app.schemas.article import ArticleOut
from app.schemas.brief import BriefOut
from app.schemas.topic import TopicOut

router = APIRouter(prefix="/api")


@router.get("/topics", response_model=list[TopicOut])
def list_topics(db: Session = Depends(get_db)):
    return topic_repository.get_all(db, enabled_only=False)


@router.get("/topics/{slug}", response_model=TopicOut)
def get_topic(slug: str, db: Session = Depends(get_db)):
    topic = topic_repository.get_by_slug(db, slug)
    if not topic:
        raise HTTPException(status_code=404, detail="Not found")
    return topic


@router.get("/topics/{slug}/articles", response_model=list[ArticleOut])
def get_topic_articles(
    slug: str,
    sort: str = "newest",
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    topic = topic_repository.get_by_slug(db, slug)
    if not topic:
        raise HTTPException(status_code=404, detail="Not found")
    return article_repository.get_by_topic(db, topic.id, limit=limit, offset=offset, sort=sort)


@router.get("/topics/{slug}/brief", response_model=BriefOut)
def get_topic_brief(slug: str, db: Session = Depends(get_db)):
    topic = topic_repository.get_by_slug(db, slug)
    if not topic:
        raise HTTPException(status_code=404, detail="Not found")
    brief = brief_repository.get_by_topic(db, topic.id)
    if not brief:
        raise HTTPException(status_code=404, detail="No brief available")
    return brief
