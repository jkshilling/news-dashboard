from __future__ import annotations
"""
Deterministic topic matching and relevance scoring.
No AI involved — purely rules-based.
"""
from app.models.topic import Topic


def _tokenize(text: str) -> str:
    import re
    text = (text or "").lower()
    # Strip possessives so "Alaska's" matches "Alaska"
    text = re.sub(r"\u2019s\b|'s\b", " ", text)
    return text


def match_article_to_topic(
    headline: str,
    snippet: str,
    body: str,
    topic: Topic,
    source_slug: str = "",
) -> dict:
    """
    Returns a match result dict:
      matches: bool
      relevance_score: float 0–1
      matched_terms: list[str]
      excluded_term_hits: list[str]
      match_reason: str
    """
    # Source scope check — if override is set, only process listed sources
    if topic.source_scope_override:
        if source_slug not in topic.source_scope_override:
            return _no_match(reason="source not in scope")

    title_text = _tokenize(headline)
    snippet_text = _tokenize(snippet)
    body_text = _tokenize(body)
    full_text = f"{title_text} {snippet_text} {body_text}"

    # Exclusion check — any exclude hit disqualifies the article entirely
    excluded_hits = [
        term for term in (topic.exclude_terms or []) if _tokenize(term) in full_text
    ]
    if excluded_hits:
        return _no_match(excluded_term_hits=excluded_hits, reason=f"excluded: {', '.join(excluded_hits)}")

    score = 0.0
    matched = []

    # Query term scoring — title matches weight most
    for term in topic.query_terms or []:
        tl = _tokenize(term)
        if tl in title_text:
            score += 0.5
            matched.append(f"{term}[title]")
        elif tl in snippet_text:
            score += 0.25
            matched.append(f"{term}[snippet]")
        elif tl in body_text:
            score += 0.10
            matched.append(f"{term}[body]")

    if not matched:
        return _no_match(reason="no query terms matched")

    # Include term boosts
    for term in topic.include_terms or []:
        if _tokenize(term) in full_text:
            score += 0.08
            matched.append(f"+{term}")

    score = round(min(score, 1.0), 3)
    reason = f"Matched: {', '.join(matched)}"

    return {
        "matches": score >= 0.10,
        "relevance_score": score,
        "matched_terms": matched,
        "excluded_term_hits": [],
        "match_reason": reason,
    }


def _no_match(
    excluded_term_hits: list[str] | None = None,
    reason: str = "",
) -> dict:
    return {
        "matches": False,
        "relevance_score": 0.0,
        "matched_terms": [],
        "excluded_term_hits": excluded_term_hits or [],
        "match_reason": reason,
    }
