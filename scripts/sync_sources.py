"""Sync sources from config/sources.json into the database."""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import all models so SQLAlchemy can resolve relationships
from app.db import SessionLocal
import app.models.article  # noqa
import app.models.pull_status  # noqa
import app.models.brief  # noqa
import app.models.topic  # noqa
from app.models.source import Source

db = SessionLocal()

with open("config/sources.json") as f:
    sources_cfg = json.load(f)

cfg_by_slug = {s["slug"]: s for s in sources_cfg}

for source in db.query(Source).all():
    if source.slug in cfg_by_slug:
        cfg = cfg_by_slug[source.slug]
        source.active = cfg["active"]
        source.feed_url = cfg["feed_url"]
        print(f"Updated  {source.slug}: active={source.active}")

existing_slugs = {s.slug for s in db.query(Source).all()}
for cfg in sources_cfg:
    if cfg["slug"] not in existing_slugs:
        new_source = Source(
            name=cfg["name"],
            slug=cfg["slug"],
            homepage=cfg["homepage"],
            source_type=cfg["source_type"],
            feed_url=cfg["feed_url"],
            category_tag=cfg.get("category_tag"),
            bias_tag=cfg.get("bias_tag"),
            fetch_priority=cfg.get("fetch_priority", 2),
            active=cfg["active"],
            parser_strategy=cfg.get("parser_strategy", "default"),
        )
        db.add(new_source)
        print(f"Added    {cfg['slug']}: active={cfg['active']}")

db.commit()
db.close()
print("Done.")
