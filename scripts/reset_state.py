"""
Reset operational state: clears articles, briefs, and pull_status records.
Topics and sources are preserved.

Usage:
    python scripts/reset_state.py
    python scripts/reset_state.py --confirm    # skip interactive prompt
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Reset operational state (articles, briefs, status)")
    parser.add_argument("--confirm", action="store_true", help="Skip confirmation prompt")
    args = parser.parse_args()

    if not args.confirm:
        answer = input(
            "This will delete all articles, briefs, and pull status records.\n"
            "Topics and sources will be preserved.\n"
            "Continue? [y/N] "
        ).strip().lower()
        if answer != "y":
            print("Aborted.")
            sys.exit(0)

    from app.db import init_db, SessionLocal
    from app.models.article import Article
    from app.models.brief import Brief
    from app.models.pull_status import PullStatus

    init_db()
    db = SessionLocal()
    try:
        n_articles = db.query(Article).delete()
        n_briefs = db.query(Brief).delete()
        n_status = db.query(PullStatus).delete()
        db.commit()
        print(f"Deleted: {n_articles} articles, {n_briefs} briefs, {n_status} status records.")
        print("Topics and sources untouched.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
