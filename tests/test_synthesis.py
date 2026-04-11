"""
Tests for synthesis schema validation and the stub brief path.
No OpenAI calls are made — uses the stub path or direct schema validation.
"""
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from app.schemas.brief import BriefSchema, NarrativeFrame, VALID_FRAME_STATUSES, VALID_SENTIMENT_LABELS


class TestBriefSchemaValidation:
    def _valid_payload(self):
        return {
            "topline": "AI regulation is accelerating globally.",
            "executive_summary": "Major regulatory activity across the EU and US.",
            "main_themes": ["EU AI Act enforcement", "FTC investigation"],
            "what_changed": "New sources entered coverage.",
            "emerging_angles": ["Liability framework debate"],
            "consensus": ["High-risk AI will face mandatory assessment"],
            "disagreement": ["Industry disputes compliance timeline"],
            "sentiment_summary": "Predominantly procedural with speculative undertones.",
            "sentiment_labels": ["procedural", "speculative"],
            "coverage_asymmetries": ["EU coverage more technical than US"],
            "watch_items": ["FTC document demands"],
            "narrative_frames": [
                {"label": "Regulatory Race", "status": "dominant", "evidence": "Both EU and US acting."}
            ],
            "generated_at": None,
        }

    def test_valid_payload_parses_correctly(self):
        schema = BriefSchema.model_validate(self._valid_payload())
        assert schema.topline == "AI regulation is accelerating globally."
        assert len(schema.narrative_frames) == 1
        assert schema.narrative_frames[0].status == "dominant"

    def test_invalid_frame_status_coerced_to_emerging(self):
        payload = self._valid_payload()
        payload["narrative_frames"] = [
            {"label": "Test Frame", "status": "nonsense_status", "evidence": "Evidence here."}
        ]
        schema = BriefSchema.model_validate(payload)
        assert schema.narrative_frames[0].status == "emerging"

    def test_invalid_sentiment_label_coerced_to_neutral(self):
        payload = self._valid_payload()
        payload["sentiment_labels"] = ["procedural", "totally_made_up_label"]
        schema = BriefSchema.model_validate(payload)
        assert "procedural" in schema.sentiment_labels
        assert "neutral" in schema.sentiment_labels
        assert "totally_made_up_label" not in schema.sentiment_labels

    def test_missing_optional_fields_use_defaults(self):
        minimal = {
            "topline": "Something happened.",
            "executive_summary": "Details unclear.",
        }
        schema = BriefSchema.model_validate(minimal)
        assert schema.main_themes == []
        assert schema.sentiment_labels == []
        assert schema.narrative_frames == []
        assert schema.what_changed == ""

    def test_narrative_frames_as_non_list_coerced_to_empty(self):
        payload = self._valid_payload()
        payload["narrative_frames"] = "not a list"
        schema = BriefSchema.model_validate(payload)
        assert schema.narrative_frames == []

    def test_all_valid_frame_statuses_accepted(self):
        for status in VALID_FRAME_STATUSES:
            frame = NarrativeFrame(label="Test", status=status, evidence="Evidence.")
            assert frame.status == status

    def test_all_valid_sentiment_labels_accepted(self):
        payload = self._valid_payload()
        payload["sentiment_labels"] = list(VALID_SENTIMENT_LABELS)
        schema = BriefSchema.model_validate(payload)
        assert set(schema.sentiment_labels) == VALID_SENTIMENT_LABELS


class TestStubBrief:
    def test_stub_brief_generated_without_api_key(self):
        """synthesis_service returns a stub brief when OPENAI_API_KEY is empty."""
        from app.services.synthesis_service import _stub_brief

        topic = MagicMock()
        topic.name = "AI Regulation"
        topic.slug = "ai-regulation"

        digest = (
            "[1] Reuters | 2024-03-15\nHEADLINE: EU AI Act enters enforcement phase\n"
            "TEXT: European Union officials confirmed...\n\n"
            "[2] Politico | 2024-03-14\nHEADLINE: Senate roadmap released for AI legislation\n"
            "TEXT: Bipartisan senators released...\n"
        )

        stub = _stub_brief(topic, digest, "Initial brief. No prior baseline.")
        assert isinstance(stub, BriefSchema)
        assert "[Demo]" in stub.topline
        assert stub.sentiment_labels == ["neutral"]
        assert len(stub.watch_items) > 0
        assert stub.what_changed == "Initial brief. No prior baseline."

    def test_stub_brief_frame_status_is_valid(self):
        from app.services.synthesis_service import _stub_brief

        topic = MagicMock()
        topic.name = "Test Topic"
        topic.slug = "test"

        stub = _stub_brief(topic, "", "")
        for frame in stub.narrative_frames:
            if isinstance(frame, dict):
                assert frame.get("status") in VALID_FRAME_STATUSES
            else:
                assert frame.status in VALID_FRAME_STATUSES


class TestNarrativeService:
    def test_initial_brief_message(self):
        from app.services.narrative_service import compute_what_changed
        result = compute_what_changed(articles=[], previous_brief=None, topic_name="AI Regulation")
        assert "Initial brief" in result

    def test_volume_spike_detected(self):
        from app.services.narrative_service import compute_what_changed

        articles = [MagicMock() for _ in range(15)]
        for a in articles:
            a.source = None

        prev = {"article_count": 3, "sentiment_labels": [], "narrative_frames": [], "_source_slugs": []}
        result = compute_what_changed(articles, prev, "Test Topic")
        assert "volume" in result.lower() or "3 →" in result or "15" in result

    def test_no_changes_produces_consistent_message(self):
        from app.services.narrative_service import compute_what_changed

        articles = [MagicMock() for _ in range(5)]
        for a in articles:
            a.source = None

        prev = {
            "article_count": 5,
            "sentiment_labels": [],
            "narrative_frames": [],
            "_source_slugs": [],
        }
        result = compute_what_changed(articles, prev, "Test Topic")
        assert isinstance(result, str)
        assert len(result) > 0
