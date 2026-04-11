from __future__ import annotations
"""
Rules-based sentiment classification.
Classifies a text sample against the allowed sentiment label vocabulary.
Used to cross-check or supplement AI-reported labels deterministically.
"""
import re

SENTIMENT_SIGNALS: dict[str, list[str]] = {
    "alarmed": [
        "warning", "crisis", "urgent", "threat", "danger", "alarming",
        "emergency", "catastrophe", "severe", "critical attack", "breach",
        "collapse", "escalat",
    ],
    "celebratory": [
        "breakthrough", "milestone", "historic", "landmark", "victory",
        "success", "celebrate", "achievement", "record high", "wins",
    ],
    "skeptical": [
        "doubt", "question", "skeptic", "unverified", "claim", "alleged",
        "disputed", "unclear", "whether", "if true", "critics say",
    ],
    "adversarial": [
        "clash", "conflict", "opposition", "confrontation", "rival",
        "versus", "dispute", "attack", "counter", "fight back",
    ],
    "procedural": [
        "filed", "approved", "passed", "signed", "announced", "confirmed",
        "committee", "hearing", "vote", "regulation", "ruling",
    ],
    "speculative": [
        "could", "might", "may", "possible", "potential", "expected to",
        "anticipated", "likely", "forecast", "prediction", "analysts say",
    ],
    "condemnatory": [
        "condemn", "criticize", "slam", "denounce", "reject", "outrage",
        "unacceptable", "failure", "disgrace", "accountability",
    ],
}


def classify_text(text: str) -> list[str]:
    """Return up to 3 dominant sentiment labels for a block of text."""
    if not text:
        return ["neutral"]

    lower = text.lower()
    scores: dict[str, int] = {}

    for label, signals in SENTIMENT_SIGNALS.items():
        count = sum(1 for sig in signals if sig in lower)
        if count:
            scores[label] = count

    if not scores:
        return ["neutral"]

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [label for label, _ in ranked[:3]]
