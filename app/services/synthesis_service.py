from __future__ import annotations
"""
AI synthesis service.
Builds a brief for a topic by sending deduplicated articles to OpenAI
and coercing the response into the BriefSchema contract.
"""
import json
import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.config import settings
from app.models.topic import Topic
from app.repositories import (
    article_repository,
    brief_repository,
    status_repository,
)
from app.schemas.brief import BriefSchema
from app.services import dedupe_service, extract_service, narrative_service

log = logging.getLogger(__name__)


def run_synthesis(db: Session, force: bool = False) -> dict:
    """Run synthesis for all enabled topics that need it."""
    from app.repositories import topic_repository

    topics = topic_repository.get_all(db, enabled_only=True)
    results = {}

    for topic in topics:
        log.info("Synthesising topic: %s", topic.slug)
        try:
            brief = synthesise_topic(db, topic, force=force)
            results[topic.slug] = "ok" if brief else "skipped"
        except Exception as exc:
            log.error("Synthesis failed for %s: %s", topic.slug, exc)
            results[topic.slug] = f"error: {exc}"
            status_repository.upsert(
                db,
                topic_id=topic.id,
                source_id=None,
                attempted=True,
                succeeded=False,
                error=str(exc)[:500],
                synthesis_status="failed",
            )

    return results


def synthesise_topic(db: Session, topic: Topic, force: bool = False) -> BriefSchema | None:
    """Generate and persist a brief for one topic. Returns None if skipped."""
    candidates = article_repository.get_synthesis_candidates(db, topic.id, limit=80)

    if not candidates:
        log.info("No articles for %s — skipping synthesis", topic.slug)
        return None

    if not force and len(candidates) < settings.SYNTHESIS_MIN_NEW_ARTICLES:
        log.info("Too few articles (%d) for %s — skipping", len(candidates), topic.slug)
        return None

    # Reduce to deduplicated synthesis set
    synthesis_set = dedupe_service.build_synthesis_set(candidates)
    log.info("Synthesis set for %s: %d articles (from %d)", topic.slug, len(synthesis_set), len(candidates))

    # Optionally extract fuller text for the top articles
    _enrich_body_text(db, synthesis_set[:10])

    # Get previous brief for change detection
    existing_brief = brief_repository.get_by_topic(db, topic.id)
    prev_data = existing_brief.previous_brief_data if existing_brief else None
    if existing_brief and not prev_data:
        # Use existing brief fields as prev_data snapshot
        prev_data = {
            "topline": existing_brief.topline,
            "sentiment_labels": existing_brief.sentiment_labels,
            "narrative_frames": existing_brief.narrative_frames,
            "article_count": existing_brief.article_count,
            "_source_slugs": narrative_service.build_source_snapshot(candidates),
        }

    what_changed = narrative_service.compute_what_changed(
        articles=synthesis_set,
        previous_brief=prev_data,
        topic_name=topic.name,
    )

    article_digest = _build_article_digest(synthesis_set)

    status_repository.upsert(
        db, topic_id=topic.id, source_id=None, attempted=True, synthesis_status="running"
    )

    brief_schema = _call_openai(topic, article_digest, what_changed)

    if brief_schema is None:
        status_repository.upsert(
            db, topic_id=topic.id, source_id=None, synthesis_status="failed",
            error="OpenAI call returned no usable result"
        )
        return None

    brief_schema.generated_at = datetime.utcnow()

    brief_repository.upsert(db, topic.id, brief_schema, article_count=len(synthesis_set))

    status_repository.upsert(
        db,
        topic_id=topic.id,
        source_id=None,
        attempted=True,
        succeeded=True,
        items_found=len(candidates),
        items_stored=len(synthesis_set),
        synthesis_status="done",
        synthesis_ran=True,
    )

    log.info("Brief generated for %s: %s", topic.slug, brief_schema.topline[:80])
    return brief_schema


def _enrich_body_text(db: Session, articles: list) -> None:
    """Fetch body text for articles that don't have it yet."""
    for article in articles:
        if article.body_text:
            continue
        text = extract_service.extract_text(article.url)
        if text:
            article.body_text = text
            db.commit()


def _build_article_digest(articles: list) -> str:
    """Build a compact text digest of articles for the prompt."""
    lines = []
    for i, a in enumerate(articles, 1):
        source_name = a.source.name if a.source else "Unknown"
        date_str = a.published_at.strftime("%Y-%m-%d") if a.published_at else "n/d"
        text = a.body_text or a.snippet or ""
        text_snippet = text[:300].replace("\n", " ")
        lines.append(
            f"[{i}] {source_name} | {date_str}\n"
            f"HEADLINE: {a.headline}\n"
            f"TEXT: {text_snippet}\n"
        )
    return "\n".join(lines)


def _call_openai(topic: Topic, article_digest: str, what_changed: str) -> BriefSchema | None:
    if not settings.OPENAI_API_KEY:
        log.warning("No OPENAI_API_KEY set — returning stub brief")
        return _stub_brief(topic, article_digest, what_changed)

    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.OPENAI_API_KEY)

        system_prompt = _load_prompt(settings.SYNTHESIS_SYSTEM_PROMPT)
        user_template = _load_prompt(settings.SYNTHESIS_USER_PROMPT)
        article_count = len(article_digest.split("\n[")) - 1 or 1
        user_prompt = user_template.format(
            topic_name=topic.name,
            topic_description=topic.description or "",
            query_terms=", ".join(topic.query_terms or []),
            article_digest=article_digest,
            article_digest_count=article_count,
            what_changed=what_changed,
        )

        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            max_tokens=settings.OPENAI_MAX_TOKENS,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        raw_json = response.choices[0].message.content
        data = json.loads(raw_json)
        return BriefSchema.model_validate(data)

    except Exception as exc:
        log.error("OpenAI synthesis error for %s: %s", topic.slug, exc)
        raise


def _load_prompt(path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _stub_brief(topic: Topic, article_digest: str, what_changed: str) -> BriefSchema:
    """Return a minimal stub brief when no OpenAI key is configured."""
    headlines = [
        line.replace("HEADLINE: ", "").strip()
        for line in article_digest.splitlines()
        if line.startswith("HEADLINE:")
    ][:5]

    topline = f"[Demo] {len(headlines)} recent articles indexed for {topic.name}."
    return BriefSchema(
        topline=topline,
        executive_summary=(
            f"This is a stub brief generated without an OpenAI API key. "
            f"Sample headlines include: {'; '.join(headlines[:3])}."
        ),
        main_themes=[f"Coverage of {topic.name}", "Multiple sources reporting"],
        what_changed=what_changed,
        emerging_angles=["Live synthesis requires OPENAI_API_KEY to be set."],
        consensus=["Monitoring active across configured sources."],
        disagreement=[],
        sentiment_summary="neutral — stub brief",
        sentiment_labels=["neutral"],
        coverage_asymmetries=[],
        watch_items=["Configure OPENAI_API_KEY in .env to enable full synthesis."],
        narrative_frames=[
            {"label": "Monitoring Active", "status": "dominant", "evidence": topline}
        ],
        generated_at=datetime.utcnow(),
    )
