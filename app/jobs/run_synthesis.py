"""
CLI entrypoint for the synthesis (brief generation) job.

Usage:
    python -m app.jobs.run_synthesis
    python -m app.jobs.run_synthesis --force       # bypass minimum article threshold
    python -m app.jobs.run_synthesis --topic slug  # single topic
"""
import argparse
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    stream=sys.stdout,
)

log = logging.getLogger("run_synthesis")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run AI synthesis job")
    parser.add_argument("--force", action="store_true", help="Bypass minimum article threshold")
    parser.add_argument("--topic", default=None, help="Run for a single topic slug")
    args = parser.parse_args()

    from app.db import SessionLocal, init_db
    from app.services.synthesis_service import run_synthesis, synthesise_topic
    from app.repositories.topic_repository import get_by_slug

    init_db()
    db = SessionLocal()
    try:
        if args.topic:
            topic = get_by_slug(db, args.topic)
            if not topic:
                log.error("Topic '%s' not found", args.topic)
                sys.exit(1)
            brief = synthesise_topic(db, topic, force=args.force)
            if brief:
                log.info("Brief generated: %s", brief.topline)
            else:
                log.info("Synthesis skipped (insufficient articles or already current).")
        else:
            results = run_synthesis(db, force=args.force)
            for slug, status in results.items():
                log.info("  %s: %s", slug, status)
    finally:
        db.close()


if __name__ == "__main__":
    main()
