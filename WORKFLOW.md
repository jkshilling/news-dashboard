# Development & Deploy Workflow

## 1. Run locally
```bash
cd /Users/jordanshilling/Documents/Claude/news-intel-dashboard
source .venv/bin/activate
uvicorn app.main:app --reload
```
Open http://localhost:8000 to preview changes.

## 2. Commit and push to GitHub
```bash
git add -A
git commit -m "describe your change"
git push
```

## 3. Deploy to production
```bash
ssh root@134.199.227.30
cd /opt/news-intel-dashboard && git pull && systemctl restart news-intel
```

## 4. Sync sources (after adding/changing sources.json)
```bash
source .venv/bin/activate && python scripts/sync_sources.py
```

## 5. Manually trigger collection
```bash
source .venv/bin/activate && python scripts/run_collection.py
```

Site is live at https://akledger.com

---

## Notes
- Never commit `.env` (it has your real API key)
- Database lives only on the server — not in git
- Scheduler restarts with the service (collection hourly, synthesis daily)
