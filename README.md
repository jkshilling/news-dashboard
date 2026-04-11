# News Intel Dashboard

A local-first, modular intelligence monitoring dashboard for tracking a curated set of news topics across a hardcoded source list. The system pulls fresh coverage on a schedule and generates AI-written narrative briefs per topic.

This is not a generic news reader. It is a synthesis-and-routing dashboard. The UI is dark, editorial, and restrained.

---

## What It Does

- Monitors a manually defined set of topics loaded from `config/topics.json`
- Fetches articles from curated sources defined in `config/sources.json` (RSS-first, scrape fallback)
- Matches articles to topics using deterministic term-matching rules — no AI at this stage
- Scores each article match by relevance (0–1)
- Generates a structured AI brief per topic via the OpenAI API
- Surfaces everything through a minimal dark web UI: homepage, topic detail pages, status page
- Exposes lightweight JSON API endpoints for internal inspection

The app is fully functional without an OpenAI API key using sample data and a stub brief generator.

---

## Architecture Overview

```
config/           Topic and source definitions + AI prompt templates
app/
  config.py       Settings loaded from .env
  db.py           SQLAlchemy engine, Base, session factory
  models/         ORM models: Topic, Source, Article, Brief, PullStatus
  schemas/        Pydantic schemas for validation and API output
  repositories/   Database access layer (per-model)
  services/
    topic_matcher   Deterministic article-topic matching (no AI)
    rss_service     RSS feed fetching via feedparser
    scrape_service  HTML listing page scraping via httpx + BeautifulSoup
    extract_service Article body extraction via trafilatura
    dedupe_service  URL normalisation + headline similarity deduplication
    ingest_service  Pipeline orchestrator: fetch → match → store
    synthesis_service   OpenAI brief generation + schema coercion
    narrative_service   Rules-based change detection between briefs
    sentiment_service   Keyword-based sentiment classification
    status_service  Status aggregation for homepage and status page
  routes/         FastAPI routes: pages (HTML) + API endpoints
  jobs/           run_collection.py, run_synthesis.py, scheduler.py
  templates/      Jinja2 HTML templates
  static/         CSS and minimal JS
scripts/          Bootstrap, seed, and reset utilities
tests/            pytest test suite
data/             SQLite database + sample payloads
```

---

## Folder Structure

```
news-intel-dashboard/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── db.py
│   ├── models/         (topic, source, article, brief, pull_status)
│   ├── schemas/        (topic, article, brief, status)
│   ├── services/       (10 service modules)
│   ├── repositories/   (5 repository modules)
│   ├── routes/         (pages, api_topics, api_status)
│   ├── jobs/           (run_collection, run_synthesis, scheduler)
│   ├── templates/      (base, index, topic_detail, status + 4 partials)
│   └── static/         (styles.css, topic_filters.js)
├── config/
│   ├── topics.json
│   ├── sources.json
│   └── prompt_templates/
│       ├── synthesis_system.txt
│       └── synthesis_user.txt
├── data/
│   └── sample_payloads/
├── scripts/
│   ├── bootstrap.py
│   ├── seed_topics.py
│   ├── seed_sources.py
│   └── reset_state.py
├── tests/
├── .env.example
├── requirements.txt
└── docker-compose.optional.yml
```

---

## Local Setup

**Requirements:** Python 3.12+

```bash
# 1. Clone and enter the project
cd news-intel-dashboard

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate      # macOS/Linux
# .venv\Scripts\activate       # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env — at minimum set OPENAI_API_KEY if you want live synthesis

# 5. Bootstrap the database (creates tables, seeds topics and sources)
python scripts/bootstrap.py

# 6. (Optional) Load sample data for immediate demo without live fetching
python scripts/bootstrap.py --sample-data
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | (empty) | Required for live synthesis. App runs in stub mode without it. |
| `DATABASE_URL` | `sqlite:///./data/app.db` | SQLAlchemy database URL |
| `APP_ENV` | `development` | `development` enables `/api/docs` |
| `MAX_ARTICLES_PER_TOPIC` | `100` | Retention limit — oldest articles pruned beyond this |
| `COLLECTION_INTERVAL_MINUTES` | `60` | Scheduler collection cadence |
| `SYNTHESIS_INTERVAL_HOURS` | `24` | Scheduler synthesis cadence |
| `SYNTHESIS_MIN_NEW_ARTICLES` | `5` | Minimum new articles to trigger synthesis |
| `REQUEST_TIMEOUT_SECONDS` | `20` | HTTP timeout for all outbound requests |
| `USER_AGENT` | `NewsIntelDashboard/1.0` | User-agent string for outbound requests |
| `ENABLE_SCHEDULER` | `false` | Start APScheduler in-process with the web server |

---

## How to Seed Topics and Sources

Topics and sources are defined in `config/topics.json` and `config/sources.json`. Edit those files to add or modify entries, then re-run:

```bash
python scripts/seed_topics.py
python scripts/seed_sources.py
```

Or run `bootstrap.py` which does both:

```bash
python scripts/bootstrap.py
```

Topics and sources use upsert logic — safe to re-run after edits.

---

## How to Run the Web App

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000` in your browser.

API documentation (development mode only): `http://localhost:8000/api/docs`

---

## How to Run Collection Manually

Fetch articles from all active sources and match them to topics:

```bash
python -m app.jobs.run_collection
```

---

## How to Run Synthesis Manually

Generate AI briefs for all enabled topics:

```bash
python -m app.jobs.run_synthesis

# Force run (bypass minimum article threshold):
python -m app.jobs.run_synthesis --force

# Run for a single topic by slug:
python -m app.jobs.run_synthesis --topic ai-regulation
```

Requires `OPENAI_API_KEY` in `.env`. Without it, a stub brief is generated instead.

---

## Sample Cron Examples

For production deployment, disable the in-process scheduler (`ENABLE_SCHEDULER=false`) and use system cron or a job runner instead.

```cron
# Collect articles every hour
0 * * * * cd /opt/news-intel-dashboard && .venv/bin/python -m app.jobs.run_collection >> /var/log/intel-collect.log 2>&1

# Run synthesis daily at 06:00 UTC
0 6 * * * cd /opt/news-intel-dashboard && .venv/bin/python -m app.jobs.run_synthesis >> /var/log/intel-synthesis.log 2>&1
```

Alternatively, enable the in-process scheduler for simpler single-process deployments:

```env
ENABLE_SCHEDULER=true
```

---

## Retention Behavior

The app is designed for **current-state monitoring only**, not archival.

- **Articles:** Only the most recent `MAX_ARTICLES_PER_TOPIC` articles per topic are kept. After each collection run, older articles are pruned automatically.
- **Briefs:** One brief per topic is stored. When synthesis runs, the previous brief is archived as a JSON blob inside the current record (for change comparison) before being overwritten.
- **Pull status:** One status record per source and per topic. Always reflects the latest run only.

There are no historical logs, daily snapshots, or audit trails in the database.

---

## Adding a New Topic

1. Edit `config/topics.json` and add a new entry following the existing format.
2. Run `python scripts/seed_topics.py` to upsert into the database.
3. Run `python -m app.jobs.run_collection` to fetch matching articles.
4. Run `python -m app.jobs.run_synthesis --topic your-new-slug` to generate its first brief.

---

## Adding a New Source

1. Edit `config/sources.json` and add a new entry.
2. Set `source_type` to `rss` (preferred), `scrape`, or `api`.
3. For RSS sources, provide `feed_url`. For scrape sources, provide `listing_url` and optionally `article_url_pattern` (regex).
4. Run `python scripts/seed_sources.py`.
5. The next collection run will include the new source.

---

## Running Tests

```bash
pip install pytest httpx  # httpx required for TestClient
pytest tests/ -v
```

Tests use an in-memory SQLite database — no external services required.

---

## Resetting State

To clear all articles, briefs, and pull status records while preserving topics and sources:

```bash
python scripts/reset_state.py
```

---

## Future Deployment Notes

### GitHub

The project is structured for straightforward Git use. The `.gitignore` excludes:
- `.env` (secrets)
- `data/app.db` (generated database)
- `__pycache__` and build artifacts

### Docker / DigitalOcean

A `docker-compose.optional.yml` is included as a starting point. To fully containerize:

1. Create a `Dockerfile.optional` at project root:
   ```dockerfile
   FROM python:3.12-slim
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   COPY . .
   RUN python scripts/bootstrap.py
   CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
   ```

2. Mount `./data` as a volume to persist the SQLite database across container restarts.

3. For DigitalOcean App Platform or a Droplet:
   - Use `gunicorn` with `uvicorn` workers for production: `gunicorn app.main:app -w 2 -k uvicorn.workers.UvicornWorker`
   - Put nginx in front for static file serving and TLS termination
   - For higher traffic, migrate `DATABASE_URL` to PostgreSQL (SQLAlchemy supports it with no model changes)

### Scheduler vs. Cron

For production, prefer real system cron over the in-process APScheduler (`ENABLE_SCHEDULER=false`). The in-process scheduler is fine for local development but can cause issues with multi-worker deployments.
