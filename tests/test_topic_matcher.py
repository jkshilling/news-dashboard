"""
Tests for deterministic topic matching logic.
No database or external calls required.
"""
import pytest
from unittest.mock import MagicMock

from app.services.topic_matcher import match_article_to_topic


def make_topic(
    query_terms=None,
    include_terms=None,
    exclude_terms=None,
    source_scope_override=None,
):
    topic = MagicMock()
    topic.query_terms = query_terms or []
    topic.include_terms = include_terms or []
    topic.exclude_terms = exclude_terms or []
    topic.source_scope_override = source_scope_override or []
    return topic


class TestBasicMatching:
    def test_title_match_gives_high_score(self):
        topic = make_topic(query_terms=["AI regulation"])
        result = match_article_to_topic(
            headline="EU AI regulation passes final vote",
            snippet="",
            body="",
            topic=topic,
        )
        assert result["matches"] is True
        assert result["relevance_score"] >= 0.5

    def test_snippet_only_match_gives_lower_score(self):
        topic = make_topic(query_terms=["AI regulation"])
        result = match_article_to_topic(
            headline="Parliament votes on landmark tech bill",
            snippet="The measure includes AI regulation provisions.",
            body="",
            topic=topic,
        )
        assert result["matches"] is True
        assert result["relevance_score"] < 0.5

    def test_body_only_match_gives_lowest_score(self):
        topic = make_topic(query_terms=["AI regulation"])
        result = match_article_to_topic(
            headline="Tech companies face new rules",
            snippet="Brussels announced sweeping measures.",
            body="Among the provisions is new AI regulation language that affects developers.",
            topic=topic,
        )
        assert result["matches"] is True
        assert result["relevance_score"] < 0.25

    def test_no_match_returns_false(self):
        topic = make_topic(query_terms=["AI regulation"])
        result = match_article_to_topic(
            headline="Stock market hits record high",
            snippet="Investors cheered the economic news.",
            body="",
            topic=topic,
        )
        assert result["matches"] is False
        assert result["relevance_score"] == 0.0

    def test_matched_terms_populated(self):
        topic = make_topic(query_terms=["ransomware", "data breach"])
        result = match_article_to_topic(
            headline="Ransomware attack causes data breach at hospital",
            snippet="",
            body="",
            topic=topic,
        )
        assert result["matches"] is True
        assert any("ransomware" in t.lower() for t in result["matched_terms"])
        assert any("data breach" in t.lower() for t in result["matched_terms"])


class TestExclusionLogic:
    def test_exclude_term_disqualifies_article(self):
        topic = make_topic(
            query_terms=["AI regulation"],
            exclude_terms=["AI image generator tutorial"],
        )
        result = match_article_to_topic(
            headline="AI regulation: what the EU AI image generator tutorial ban means",
            snippet="",
            body="",
            topic=topic,
        )
        assert result["matches"] is False
        assert "AI image generator tutorial" in result["excluded_term_hits"]

    def test_exclusion_in_snippet_also_disqualifies(self):
        topic = make_topic(
            query_terms=["cybersecurity"],
            exclude_terms=["cybersecurity course"],
        )
        result = match_article_to_topic(
            headline="Cybersecurity market update",
            snippet="Sign up for the best cybersecurity course online.",
            body="",
            topic=topic,
        )
        assert result["matches"] is False

    def test_no_exclude_hit_passes_normally(self):
        topic = make_topic(
            query_terms=["cyberattack"],
            exclude_terms=["cybersecurity awareness month"],
        )
        result = match_article_to_topic(
            headline="Major cyberattack disrupts federal agency",
            snippet="Officials confirmed the intrusion on Tuesday.",
            body="",
            topic=topic,
        )
        assert result["matches"] is True
        assert result["excluded_term_hits"] == []


class TestIncludeBoosts:
    def test_include_terms_boost_score(self):
        topic = make_topic(
            query_terms=["energy transition"],
            include_terms=["IEA", "solar"],
        )
        boosted = match_article_to_topic(
            headline="Energy transition accelerates as IEA solar forecast rises",
            snippet="",
            body="",
            topic=topic,
        )
        unboosted = match_article_to_topic(
            headline="Energy transition accelerates globally",
            snippet="",
            body="",
            topic=topic,
        )
        assert boosted["relevance_score"] > unboosted["relevance_score"]

    def test_score_capped_at_1(self):
        topic = make_topic(
            query_terms=["AI regulation"] * 5,
            include_terms=["FTC"] * 10,
        )
        result = match_article_to_topic(
            headline="AI regulation AI regulation AI regulation",
            snippet="FTC FTC FTC investigation",
            body="",
            topic=topic,
        )
        assert result["relevance_score"] <= 1.0


class TestSourceScope:
    def test_source_in_scope_passes(self):
        topic = make_topic(
            query_terms=["AI regulation"],
            source_scope_override=["reuters", "politico"],
        )
        result = match_article_to_topic(
            headline="AI regulation update",
            snippet="",
            body="",
            topic=topic,
            source_slug="reuters",
        )
        assert result["matches"] is True

    def test_source_not_in_scope_rejected(self):
        topic = make_topic(
            query_terms=["AI regulation"],
            source_scope_override=["reuters", "politico"],
        )
        result = match_article_to_topic(
            headline="AI regulation update",
            snippet="",
            body="",
            topic=topic,
            source_slug="the-verge",
        )
        assert result["matches"] is False
        assert "scope" in result["match_reason"]

    def test_empty_scope_override_allows_all_sources(self):
        topic = make_topic(
            query_terms=["AI regulation"],
            source_scope_override=[],
        )
        result = match_article_to_topic(
            headline="AI regulation update",
            snippet="",
            body="",
            topic=topic,
            source_slug="any-source",
        )
        assert result["matches"] is True
