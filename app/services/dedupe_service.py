from __future__ import annotations
"""
Deduplication helpers.

Two separate concerns:
1. URL-level dedupe — prevents inserting the same article twice.
2. Synthesis-set dedupe — reduces near-identical articles before sending to AI,
   using canonical URL normalisation + headline similarity.
"""
import re
import urllib.parse


def canonical_url(url: str) -> str:
    """Normalise a URL for dedupe comparison: strip fragment, sort params, lowercase host."""
    try:
        p = urllib.parse.urlparse(url.strip().lower())
        # Remove utm_* and similar tracking params
        params = urllib.parse.parse_qsl(p.query)
        params = [(k, v) for k, v in params if not k.startswith("utm_")]
        clean_query = urllib.parse.urlencode(sorted(params))
        normalised = urllib.parse.urlunparse((
            p.scheme, p.netloc, p.path.rstrip("/"), p.params, clean_query, ""
        ))
        return normalised
    except Exception:
        return url


def _headline_tokens(headline: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", headline.lower())
    # Strip very common stop words
    stopwords = {"the", "a", "an", "is", "in", "on", "of", "to", "and", "for", "at", "by"}
    return {w for w in words if w not in stopwords and len(w) > 2}


def headlines_are_similar(h1: str, h2: str, threshold: float = 0.7) -> bool:
    """Jaccard similarity of headline tokens."""
    t1 = _headline_tokens(h1)
    t2 = _headline_tokens(h2)
    if not t1 or not t2:
        return False
    intersection = t1 & t2
    union = t1 | t2
    return len(intersection) / len(union) >= threshold


def build_synthesis_set(articles: list) -> list:
    """
    Reduce a list of Article ORM objects to a deduplicated set for AI synthesis.
    Keeps the highest-scoring article when near-duplicates are found.
    Does NOT mutate the original list — UI still shows all articles.
    """
    seen_urls: set[str] = set()
    seen_headlines: list[str] = []
    result = []

    # Sort by relevance descending so we keep the best-scored duplicate
    sorted_articles = sorted(articles, key=lambda a: a.relevance_score, reverse=True)

    for article in sorted_articles:
        c_url = canonical_url(article.canonical_url or article.url)
        if c_url in seen_urls:
            continue

        # Headline similarity check against already-accepted articles
        is_dup = any(
            headlines_are_similar(article.headline, h) for h in seen_headlines
        )
        if is_dup:
            continue

        seen_urls.add(c_url)
        seen_headlines.append(article.headline)
        result.append(article)

    return result
