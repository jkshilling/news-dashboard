from __future__ import annotations
"""
Narrative change-detection service.
Computes a rules-based delta between the current intake and previous brief.
Returns a human-readable "what changed" string without invoking AI.
"""
from app.models.brief import Brief
from app.models.article import Article


def compute_what_changed(
    articles: list[Article],
    previous_brief: dict | None,
    topic_name: str = "",
) -> str:
    """
    Derive a change summary string by comparing current article intake
    against the previous brief snapshot.
    """
    if not previous_brief:
        return f"Initial brief for {topic_name}. No prior baseline to compare."

    changes: list[str] = []

    # Volume delta
    prev_count = previous_brief.get("article_count", 0)
    curr_count = len(articles)
    if curr_count > prev_count * 1.5 and curr_count - prev_count >= 5:
        changes.append(f"Coverage volume up significantly ({prev_count} → {curr_count} articles).")
    elif curr_count < prev_count * 0.5 and prev_count - curr_count >= 5:
        changes.append(f"Coverage volume dropped ({prev_count} → {curr_count} articles).")

    # New sources entering the topic
    prev_sources = set(previous_brief.get("_source_slugs", []))
    curr_sources = {getattr(a.source, "slug", "") for a in articles if a.source}
    new_sources = curr_sources - prev_sources
    if new_sources:
        names = ", ".join(sorted(new_sources))
        changes.append(f"New sources entered coverage: {names}.")

    # Sentiment shift
    prev_labels = set(previous_brief.get("sentiment_labels", []))
    curr_labels_from_articles = _derive_sentiment_labels(articles)
    new_labels = curr_labels_from_articles - prev_labels
    dropped_labels = prev_labels - curr_labels_from_articles
    if new_labels:
        changes.append(f"Tone shift — new signals: {', '.join(sorted(new_labels))}.")
    if dropped_labels:
        changes.append(f"Fading tone: {', '.join(sorted(dropped_labels))}.")

    # Narrative frame comparison
    prev_frames = {f.get("label", ""): f.get("status", "") for f in (previous_brief.get("narrative_frames") or [])}
    # We can't check new frames here (not yet generated), but we can note frame count shifts
    if not prev_frames and curr_count > 10:
        changes.append("Story is gaining sufficient depth for narrative framing.")

    if not changes:
        changes.append("Coverage pattern broadly consistent with previous synthesis.")

    return " ".join(changes)


def _derive_sentiment_labels(articles: list[Article]) -> set[str]:
    from app.services.sentiment_service import classify_text

    all_text = " ".join(
        f"{a.headline} {a.snippet or ''}" for a in articles[:30]
    )
    return set(classify_text(all_text))


def build_source_snapshot(articles: list[Article]) -> list[str]:
    """Return a list of source slugs present in this article set."""
    return sorted({getattr(a.source, "slug", "") for a in articles if a.source})
