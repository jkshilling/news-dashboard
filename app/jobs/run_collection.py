"""
CLI entrypoint for the article collection job.

Usage:
    python -m app.jobs.run_collection
"""
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    stream=sys.stdout,
)

log = logging.getLogger("run_collection")


def main() -> None:
    from app.db import SessionLocal, init_db
    from app.services.ingest_service import run_collection

    init_db()
    db = SessionLocal()
    try:
        results = run_collection(db)
        log.info(
            "Collection complete — found=%d stored=%d errors=%d",
            results["found"],
            results["stored"],
            len(results["errors"]),
        )
        for err in results["errors"]:
            log.warning("  Error: %s", err)
    finally:
        db.close()


if __name__ == "__main__":
    main()
