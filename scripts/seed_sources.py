"""
Seed sources from config/sources.json into the database.

Usage:
    python scripts/seed_sources.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    from app.db import init_db, SessionLocal
    from app.config import settings
    from app.repositories.source_repository import upsert_from_config

    init_db()
    db = SessionLocal()
    try:
        data = json.loads(settings.SOURCES_CONFIG.read_text())
        for src in data:
            upsert_from_config(db, src)
            print(f"  + {src['slug']}: {src['name']} ({src['source_type']})")
        print(f"\n{len(data)} sources seeded.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
