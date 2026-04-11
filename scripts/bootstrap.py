"""
Bootstrap script: initialise the database, seed topics and sources,
and optionally load sample article/brief data for demo mode.

Usage:
    python scripts/bootstrap.py
    python scripts/bootstrap.py --sample-data   # also load demo articles/briefs
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Allow running from project root without installing the package
sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    parser = argparse.ArgumentParser(description="Bootstrap the News Intel Dashboard")
    parser.add_argument(
        "--sample-data",
        action="store_true",
        help="Seed sample articles and briefs for demo mode (no API key required)",
    )
    args = parser.parse_args()

    from app.db import init_db, SessionLocal
    from app.config import settings

    print("Initialising database…")
    init_db()
    print(f"  DB: {settings.DATABASE_URL}")

    db = SessionLocal()
    try:
        print("\nSeeding sources…")
        _seed_sources(db)

        print("\nSeeding topics…")
        _seed_topics(db)

        if args.sample_data:
            print("\nLoading sample articles and briefs…")
            _seed_sample_data(db)

        print("\nBootstrap complete.")
        if not settings.OPENAI_API_KEY:
            print("\n  Note: OPENAI_API_KEY is not set.")
            if not args.sample_data:
                print("  Run with --sample-data to populate the UI for demo mode.")
            print("  Set OPENAI_API_KEY in .env to enable live synthesis.")
    finally:
        db.close()


def _seed_sources(db):
    from app.repositories.source_repository import upsert_from_config
    from app.config import settings

    data = json.loads(settings.SOURCES_CONFIG.read_text())
    for src in data:
        upsert_from_config(db, src)
        print(f"  + {src['slug']}")
    print(f"  {len(data)} sources seeded.")


def _seed_topics(db):
    from app.repositories.topic_repository import upsert_from_config
    from app.config import settings

    data = json.loads(settings.TOPICS_CONFIG.read_text())
    for topic in data:
        upsert_from_config(db, topic)
        print(f"  + {topic['slug']}")
    print(f"  {len(data)} topics seeded.")


def _seed_sample_data(db):
    sample_articles_path = Path(__file__).parent.parent / "data" / "sample_payloads" / "sample_articles.json"
    sample_brief_path = Path(__file__).parent.parent / "data" / "sample_payloads" / "sample_brief.json"

    from app.models.article import Article
    from app.repositories.topic_repository import get_by_slug as get_topic
    from app.repositories.source_repository import get_by_slug as get_source
    from app.repositories.article_repository import url_exists, save as save_article
    from app.repositories.brief_repository import upsert as upsert_brief
    from app.schemas.brief import BriefSchema

    # Load sample articles
    articles_data = json.loads(sample_articles_path.read_text())
    stored = 0
    for a in articles_data:
        topic = get_topic(db, a["topic_slug"])
        source = get_source(db, a["source_slug"])
        if not topic or not source:
            print(f"  ! Skipping article — topic or source not found: {a['topic_slug']} / {a['source_slug']}")
            continue
        if url_exists(db, a["canonical_url"], topic.id):
            continue
        pub_at = datetime.fromisoformat(a["published_at"]) if a.get("published_at") else None
        article = Article(
            topic_id=topic.id,
            source_id=source.id,
            headline=a["headline"],
            snippet=a.get("snippet", ""),
            url=a["url"],
            canonical_url=a["canonical_url"],
            published_at=pub_at,
            fetched_at=datetime.utcnow(),
            relevance_score=a.get("relevance_score", 0.5),
            matched_terms=a.get("matched_terms", []),
            match_reason=a.get("match_reason", ""),
            excluded_term_hits=[],
            is_synthesis_candidate=True,
        )
        save_article(db, article)
        stored += 1
    print(f"  {stored} sample articles loaded.")

    # Load sample brief
    brief_data = json.loads(sample_brief_path.read_text())
    topic = get_topic(db, brief_data["topic_slug"])
    if topic:
        schema = BriefSchema.model_validate(brief_data)
        article_count = brief_data.get("article_count", 3)
        upsert_brief(db, topic.id, schema, article_count)
        print(f"  Sample brief loaded for topic: {topic.slug}")
    else:
        print(f"  ! Brief topic not found: {brief_data['topic_slug']}")


if __name__ == "__main__":
    main()
