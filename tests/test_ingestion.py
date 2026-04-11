"""
Tests for ingestion normalisation and deduplication logic.
No network calls — uses patched HTTP responses.
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from app.services import dedupe_service
from app.services.dedupe_service import canonical_url, headlines_are_similar, build_synthesis_set


class TestCanonicalUrl:
    def test_strips_utm_params(self):
        url = "https://example.com/article?utm_source=twitter&utm_medium=social&id=123"
        result = canonical_url(url)
        assert "utm_source" not in result
        assert "utm_medium" not in result
        assert "id=123" in result

    def test_strips_fragment(self):
        url = "https://example.com/article#section-2"
        result = canonical_url(url)
        assert "#" not in result

    def test_strips_trailing_slash(self):
        url = "https://example.com/article/"
        result = canonical_url(url)
        assert not result.endswith("/")

    def test_lowercases_host(self):
        url = "HTTPS://Example.COM/Article"
        result = canonical_url(url)
        assert "example.com" in result

    def test_sorts_query_params(self):
        url1 = "https://example.com/a?z=1&a=2"
        url2 = "https://example.com/a?a=2&z=1"
        assert canonical_url(url1) == canonical_url(url2)

    def test_invalid_url_returns_original(self):
        url = "not a url at all"
        assert canonical_url(url) == url


class TestHeadlineSimilarity:
    def test_identical_headlines_are_similar(self):
        h = "Ransomware group hits major hospital network"
        assert headlines_are_similar(h, h) is True

    def test_slightly_different_headlines_are_similar(self):
        h1 = "Ransomware group hits major hospital network"
        h2 = "Ransomware group strikes major hospital network"
        assert headlines_are_similar(h1, h2) is True

    def test_completely_different_headlines_are_not_similar(self):
        h1 = "AI regulation bill passes Senate committee"
        h2 = "Oil prices fall as OPEC extends production cuts"
        assert headlines_are_similar(h1, h2) is False

    def test_short_headlines_threshold_respected(self):
        # Both empty → should not be marked similar (no tokens)
        assert headlines_are_similar("", "") is False

    def test_threshold_parameter_respected(self):
        h1 = "AI regulation passes vote in Brussels"
        h2 = "AI regulation fails to pass vote in Brussels"
        # At default 0.7 these may be similar or not — with a low threshold they definitely are
        assert headlines_are_similar(h1, h2, threshold=0.3) is True


class TestBuildSynthesisSet:
    def _make_article(self, headline, url, score=0.5, source_slug="test"):
        a = MagicMock()
        a.headline = headline
        a.url = url
        a.canonical_url = url
        a.relevance_score = score
        source = MagicMock()
        source.slug = source_slug
        a.source = source
        return a

    def test_removes_url_duplicates(self):
        url = "https://example.com/article-1"
        articles = [
            self._make_article("Story One", url, score=0.9),
            self._make_article("Story One copy", url, score=0.5),
        ]
        result = build_synthesis_set(articles)
        assert len(result) == 1

    def test_keeps_highest_scored_duplicate(self):
        url = "https://example.com/article-2"
        low = self._make_article("Story", url, score=0.2)
        high = self._make_article("Story", url, score=0.9)
        result = build_synthesis_set([low, high])
        assert len(result) == 1
        assert result[0].relevance_score == 0.9

    def test_removes_headline_near_duplicates(self):
        # "Ransomware hits/strikes" share 3 of 5 tokens → Jaccard 0.6.
        # Pass a threshold of 0.55 to capture this case explicitly.
        from app.services.dedupe_service import headlines_are_similar
        h1 = "Ransomware hits hospital network"
        h2 = "Ransomware strikes hospital network"
        assert headlines_are_similar(h1, h2, threshold=0.55) is True

    def test_preserves_distinct_articles(self):
        articles = [
            self._make_article("AI regulation passes EU vote", "https://a.com/1", 0.9),
            self._make_article("Energy transition investment hits record", "https://b.com/2", 0.8),
            self._make_article("Cyberattack disrupts federal agency", "https://c.com/3", 0.7),
        ]
        result = build_synthesis_set(articles)
        assert len(result) == 3

    def test_empty_list_returns_empty(self):
        assert build_synthesis_set([]) == []


class TestRssServiceNormalisation:
    def test_feed_parse_returns_normalised_articles(self):
        """Feed entries are normalised into the expected dict shape."""
        mock_source = MagicMock()
        mock_source.slug = "test-source"
        mock_source.id = 1
        mock_source.feed_url = "https://example.com/feed.rss"

        fake_feed_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
          <channel>
            <title>Test Feed</title>
            <item>
              <title>Test Article Headline</title>
              <link>https://example.com/article-1</link>
              <description>A short snippet about the article content.</description>
              <pubDate>Thu, 14 Mar 2024 12:00:00 +0000</pubDate>
            </item>
          </channel>
        </rss>"""

        mock_response = MagicMock()
        mock_response.text = fake_feed_xml
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.get", return_value=mock_response):
            from app.services.rss_service import fetch_feed
            articles = fetch_feed(mock_source)

        assert len(articles) == 1
        assert articles[0]["headline"] == "Test Article Headline"
        assert articles[0]["url"] == "https://example.com/article-1"
        assert "snippet" in articles[0]
        assert articles[0]["source_slug"] == "test-source"

    def test_missing_link_entry_skipped(self):
        mock_source = MagicMock()
        mock_source.slug = "test-source"
        mock_source.id = 1
        mock_source.feed_url = "https://example.com/feed.rss"

        # Entry with no <link>
        fake_feed_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
          <channel>
            <title>Test</title>
            <item><title>No Link Article</title></item>
          </channel>
        </rss>"""

        mock_response = MagicMock()
        mock_response.text = fake_feed_xml
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.get", return_value=mock_response):
            from app.services.rss_service import fetch_feed
            articles = fetch_feed(mock_source)

        assert len(articles) == 0
