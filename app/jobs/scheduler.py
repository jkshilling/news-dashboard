"""
APScheduler-based in-process scheduler.
Only started when ENABLE_SCHEDULER=true in config.
Jobs can also be run independently via run_collection.py / run_synthesis.py.
"""
import logging

log = logging.getLogger(__name__)


def start_scheduler():
    from apscheduler.schedulers.background import BackgroundScheduler
    from app.config import settings
    from app.db import SessionLocal, init_db

    init_db()

    scheduler = BackgroundScheduler(timezone="America/Anchorage")

    def collection_job():
        log.info("Scheduler: starting collection job")
        from app.services.ingest_service import run_collection
        db = SessionLocal()
        try:
            run_collection(db)
        finally:
            db.close()

    def synthesis_job():
        log.info("Scheduler: starting synthesis job")
        from app.services.synthesis_service import run_synthesis
        db = SessionLocal()
        try:
            run_synthesis(db)
        finally:
            db.close()

    scheduler.add_job(
        collection_job,
        "interval",
        minutes=settings.COLLECTION_INTERVAL_MINUTES,
        id="collection",
    )
    scheduler.add_job(
        synthesis_job,
        "interval",
        hours=settings.SYNTHESIS_INTERVAL_HOURS,
        id="synthesis",
    )

    scheduler.start()
    log.info(
        "Scheduler started — collection every %dm, synthesis every %dh",
        settings.COLLECTION_INTERVAL_MINUTES,
        settings.SYNTHESIS_INTERVAL_HOURS,
    )
    return scheduler
