"""
Tests for key HTTP routes.
Uses FastAPI TestClient with an in-memory SQLite database.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app


# ---- Test database setup ----

TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module")
def client():
    # Create all tables in the in-memory DB
    from app.models import article, brief, pull_status, source, topic  # noqa: F401
    Base.metadata.create_all(bind=test_engine)

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(scope="module")
def seeded_client(client):
    """Client with topics, sources, and one article/brief seeded."""
    db = TestSessionLocal()
    try:
        from app.models.topic import Topic
        from app.models.source import Source
        from app.models.article import Article
        from app.models.brief import Brief
        from datetime import datetime

        source = Source(
            name="Test Source",
            slug="test-source",
            homepage="https://test.com",
            source_type="rss",
            feed_url="https://test.com/feed",
            active=True,
            fetch_priority=1,
            parser_strategy="default",
        )
        db.add(source)
        db.flush()

        topic = Topic(
            name="AI Regulation",
            slug="ai-regulation",
            description="Monitoring AI policy.",
            query_terms=["AI regulation"],
            include_terms=["FTC"],
            exclude_terms=[],
            source_scope_override=[],
            enabled=True,
        )
        db.add(topic)
        db.flush()

        article = Article(
            topic_id=topic.id,
            source_id=source.id,
            headline="EU AI Act enters enforcement phase",
            snippet="European regulators confirmed the timeline.",
            url="https://test.com/article-1",
            canonical_url="https://test.com/article-1",
            published_at=datetime(2024, 3, 15, 9, 0),
            relevance_score=0.85,
            matched_terms=["AI regulation[title]"],
            match_reason="Matched: AI regulation[title]",
            excluded_term_hits=[],
            is_synthesis_candidate=True,
        )
        db.add(article)

        brief = Brief(
            topic_id=topic.id,
            topline="AI regulation is accelerating globally.",
            executive_summary="Major regulatory activity across the EU and US.",
            main_themes=["EU AI Act enforcement"],
            what_changed="Initial brief.",
            emerging_angles=[],
            consensus=["High-risk AI will face assessment"],
            disagreement=[],
            sentiment_summary="Procedural.",
            sentiment_labels=["procedural"],
            coverage_asymmetries=[],
            watch_items=["FTC demands"],
            narrative_frames=[
                {"label": "Regulatory Race", "status": "dominant", "evidence": "Both regions acting."}
            ],
            generated_at=datetime(2024, 3, 15, 12, 0),
            article_count=1,
        )
        db.add(brief)

        db.commit()
    finally:
        db.close()

    return client


class TestHomepage:
    def test_homepage_returns_200(self, client):
        response = client.get("/")
        assert response.status_code == 200

    def test_homepage_contains_coverage_index(self, client):
        response = client.get("/")
        assert "Coverage Index" in response.text

    def test_homepage_shows_topics_when_seeded(self, seeded_client):
        response = seeded_client.get("/")
        assert response.status_code == 200
        assert "AI Regulation" in response.text


class TestTopicDetailPage:
    def test_valid_topic_returns_200(self, seeded_client):
        response = seeded_client.get("/topic/ai-regulation")
        assert response.status_code == 200

    def test_topic_page_shows_brief(self, seeded_client):
        response = seeded_client.get("/topic/ai-regulation")
        assert "AI regulation is accelerating globally." in response.text

    def test_topic_page_shows_article(self, seeded_client):
        response = seeded_client.get("/topic/ai-regulation")
        assert "EU AI Act enters enforcement phase" in response.text

    def test_unknown_topic_returns_404(self, client):
        response = client.get("/topic/nonexistent-slug")
        assert response.status_code == 404

    def test_sort_param_accepted(self, seeded_client):
        response = seeded_client.get("/topic/ai-regulation?sort=oldest")
        assert response.status_code == 200

    def test_source_filter_accepted(self, seeded_client):
        response = seeded_client.get("/topic/ai-regulation?source_id=1")
        assert response.status_code == 200


class TestStatusPage:
    def test_status_page_returns_200(self, client):
        response = client.get("/status")
        assert response.status_code == 200

    def test_status_page_contains_expected_heading(self, client):
        response = client.get("/status")
        assert "Pull Status" in response.text


class TestApiEndpoints:
    def test_api_topics_returns_list(self, seeded_client):
        response = seeded_client.get("/api/topics")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert any(t["slug"] == "ai-regulation" for t in data)

    def test_api_topic_by_slug(self, seeded_client):
        response = seeded_client.get("/api/topics/ai-regulation")
        assert response.status_code == 200
        assert response.json()["name"] == "AI Regulation"

    def test_api_topic_not_found(self, client):
        response = client.get("/api/topics/doesnt-exist")
        assert response.status_code == 404

    def test_api_topic_articles(self, seeded_client):
        response = seeded_client.get("/api/topics/ai-regulation/articles")
        assert response.status_code == 200
        articles = response.json()
        assert isinstance(articles, list)
        assert len(articles) >= 1
        assert articles[0]["headline"] == "EU AI Act enters enforcement phase"

    def test_api_topic_brief(self, seeded_client):
        response = seeded_client.get("/api/topics/ai-regulation/brief")
        assert response.status_code == 200
        brief = response.json()
        assert brief["topline"] == "AI regulation is accelerating globally."
        assert "procedural" in brief["sentiment_labels"]

    def test_api_status(self, client):
        response = client.get("/api/status")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
