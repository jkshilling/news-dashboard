"""
Seed topics from config/topics.json into the database.

Usage:
    python scripts/seed_topics.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    from app.db import init_db, SessionLocal
    from app.config import settings
    from app.repositories.topic_repository import upsert_from_config

    init_db()
    db = SessionLocal()
    try:
        data = json.loads(settings.TOPICS_CONFIG.read_text())
        for topic in data:
            upsert_from_config(db, topic)
            print(f"  + {topic['slug']}: {topic['name']}")
        print(f"\n{len(data)} topics seeded.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
