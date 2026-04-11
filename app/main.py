import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.db import init_db
from app.routes import api_status, api_topics, pages

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
)
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    log.info("Database initialised")
    if settings.ENABLE_SCHEDULER:
        from app.jobs.scheduler import start_scheduler
        start_scheduler()
        log.info("Background scheduler started")
    yield


app = FastAPI(
    title="News Intel Dashboard",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.APP_ENV == "development" else None,
    redoc_url=None,
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(pages.router)
app.include_router(api_topics.router)
app.include_router(api_status.router)
