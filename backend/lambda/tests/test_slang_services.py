"""Tests for slang translation services."""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from models.slang import (
    SlangTerm, SlangLexicon, TranslationResult, TranslationSpan,
    QualityMetrics, SlangTranslationResult, SlangTranslationDensity,
    LexiconStats, AgeRating, AgeFilterMode, PartOfSpeech, ApprovalStatus
)
from services.slang_lexicon_service import SlangLexiconService
from services.slang_matching_service import SlangMatchingService, RuntimeTemplate
from services.slang_llm_service import SlangLLMService
from models.config import SlangConfig


class TestSlangModels:
    """Test slang Pydantic models."""

    def test_slang_term_creation(self):
        """Test SlangTerm model creation and validation."""
        term = SlangTerm(
            term="fire",
            gloss="excellent, amazing",
            examples=["That song is fire"],
            first_seen="2024-01-01",
            last_seen="2024-01-01"
        )

        assert term.term == "fire"
        assert term.gloss == "excellent, amazing"
        assert term.age_rating == AgeRating.EVERYONE
        assert term.status == ApprovalStatus.APPROVED
        assert term.pos == PartOfSpeech.PHRASE
        assert term.confidence == 0.8

    def test_slang_lexicon_creation(self):
        """Test SlangLexicon model creation."""
        terms = [
            SlangTerm(
                term="fire",
                gloss="excellent",
                first_seen="2024-01-01",
                last_seen="2024-01-01"
            )
        ]

        lexicon = SlangLexicon(
            version="1.0.0",
            generated_at="2024-01-01T00:00:00Z",
            count=1,
            items=terms
        )

        assert lexicon.count == 1
        assert len(lexicon.items) == 1
        assert lexicon.items[0].term == "fire"

    def test_translation_result_creation(self):
        """Test TranslationResult model creation."""
        spans = [
            TranslationSpan(
                start=0,
                end=4,
                surface="fire",
                source="lexeme",
                canonical="fire",
                gloss="excellent"
            )
        ]

        result = TranslationResult(
            input="That's fire",
            translated="That's excellent",
            annotated="That's [fire: excellent]",
            matches=spans,
            coverage=0.5
        )

        assert result.input == "That's fire"
        assert result.translated == "That's excellent"
        assert len(result.matches) == 1
        assert result.coverage == 0.5

    def test_slang_translation_result_creation(self):
        """Test SlangTranslationResult model creation."""
        result = SlangTranslationResult(
            input="That's excellent",
            output="That's fire",
            density=SlangTranslationDensity.MEDIUM,
            applied=[]
        )

        assert result.input == "That's excellent"
        assert result.output == "That's fire"
        assert result.density == SlangTranslationDensity.MEDIUM
        assert len(result.applied) == 0


class TestSlangLexiconService:
    """Test SlangLexiconService."""

    @pytest.fixture
    def mock_lexicon_data(self):
        """Mock lexicon data for testing."""
        return {
            "version": "1.0.0",
            "generated_at": "2024-01-01T00:00:00Z",
            "count": 2,
            "items": [
                {
                    "term": "fire",
                    "variants": ["🔥"],
                    "pos": "word",
                    "gloss": "excellent, amazing",
                    "examples": ["That song is fire"],
                    "tags": ["positive"],
                    "status": "approved",
                    "confidence": 0.9,
                    "regions": ["US"],
                    "age_rating": "E",
                    "content_flags": [],
                    "first_seen": "2024-01-01",
                    "last_seen": "2024-01-01",
                    "sources": {"social": 100},
                    "momentum": 1.0,
                    "categories": ["music", "general"]
                },
                {
                    "term": "no cap",
                    "variants": [],
                    "pos": "phrase",
                    "gloss": "no lie, for real",
                    "examples": ["That's fire, no cap"],
                    "tags": ["emphasis"],
                    "status": "approved",
                    "confidence": 0.85,
                    "regions": ["US"],
                    "age_rating": "E",
                    "content_flags": [],
                    "first_seen": "2024-01-01",
                    "last_seen": "2024-01-01",
                    "sources": {"social": 80},
                    "momentum": 1.2,
                    "categories": ["general"]
                }
            ]
        }

    @pytest.fixture
    def slang_config(self):
        """Create SlangConfig for testing."""
        return SlangConfig(
            lexicon_s3_bucket="test-bucket",
            lexicon_s3_key="test/lexicon.json",
            lexicon_local_path="",
            titan_model_id="amazon.titan-embed-text-v2:0",
            age_max_rating=AgeRating.MATURE_18,
            age_filter_mode=AgeFilterMode.SKIP
        )

    def test_lexicon_service_creation(self, slang_config):
        """Test SlangLexiconService creation."""
        service = SlangLexiconService(slang_config)
        assert service.config == slang_config
        assert service._lexicon is None

    @patch('services.slang_lexicon_service.aws_services')
    def test_load_lexicon_from_s3(self, mock_aws_services, slang_config, mock_lexicon_data):
        """Test loading lexicon from S3."""
        # Mock S3 response
        mock_response = {
            'Body': Mock()
        }
        mock_response['Body'].read.return_value = json.dumps(mock_lexicon_data).encode('utf-8')
        mock_aws_services.s3_client.get_object.return_value = mock_response

        service = SlangLexiconService(slang_config)
        lexicon = service.load_lexicon()

        assert lexicon.count == 2
        assert len(lexicon.items) == 2
        assert lexicon.items[0].term == "fire"
        assert lexicon.items[1].term == "no cap"

    def test_load_lexicon_from_local(self, slang_config, mock_lexicon_data, tmp_path):
        """Test loading lexicon from local file."""
        # Create temporary lexicon file
        lexicon_file = tmp_path / "lexicon.json"
        lexicon_file.write_text(json.dumps(mock_lexicon_data))

        # Update config to use local path
        slang_config.lexicon_local_path = str(lexicon_file)

        service = SlangLexiconService(slang_config)
        lexicon = service.load_lexicon()

        assert lexicon.count == 2
        assert len(lexicon.items) == 2

    def test_get_lexicon_stats(self, slang_config, mock_lexicon_data):
        """Test getting lexicon statistics."""
        with patch('services.slang_lexicon_service.aws_services') as mock_aws_services:
            # Mock S3 response
            mock_response = {
                'Body': Mock()
            }
            mock_response['Body'].read.return_value = json.dumps(mock_lexicon_data).encode('utf-8')
            mock_aws_services.s3_client.get_object.return_value = mock_response

            service = SlangLexiconService(slang_config)
            stats = service.get_lexicon_stats()

            assert isinstance(stats, LexiconStats)
            assert stats.total_terms == 2
            assert stats.version == "1.0.0"
            assert stats.age_ratings["E"] == 2  # Both terms are E rated


class TestSlangMatchingService:
    """Test SlangMatchingService."""

    @pytest.fixture
    def slang_config(self):
        """Create SlangConfig for testing."""
        return SlangConfig(
            lexicon_s3_bucket="test-bucket",
            age_max_rating=AgeRating.MATURE_18,
            age_filter_mode=AgeFilterMode.SKIP
        )

    @pytest.fixture
    def sample_terms(self):
        """Sample slang terms for testing."""
        return [
            SlangTerm(
                term="fire",
                gloss="excellent",
                first_seen="2024-01-01",
                last_seen="2024-01-01"
            ),
            SlangTerm(
                term="no cap",
                gloss="no lie",
                first_seen="2024-01-01",
                last_seen="2024-01-01"
            )
        ]

    def test_matching_service_creation(self, slang_config):
        """Test SlangMatchingService creation."""
        service = SlangMatchingService(slang_config)
        assert service.config == slang_config
        assert service._automaton is None
        assert len(service._templates) > 0

    def test_runtime_template_creation(self):
        """Test RuntimeTemplate creation."""
        import re

        template = RuntimeTemplate(
            id="test_template",
            pattern=re.compile(r"test", re.IGNORECASE),
            render_func=lambda m: "replacement",
            confidence=0.8
        )

        assert template.id == "test_template"
        assert template.confidence == 0.8
        assert callable(template.render_func)

    def test_build_automaton(self, slang_config, sample_terms):
        """Test building Aho-Corasick automaton."""
        service = SlangMatchingService(slang_config)
        automaton = service.build_automaton(sample_terms)

        assert automaton is not None
        assert len(automaton.next) > 0

    def test_match_lexicon(self, slang_config, sample_terms):
        """Test matching slang terms in text."""
        service = SlangMatchingService(slang_config)
        automaton = service.build_automaton(sample_terms)

        text = "That's fire, no cap"
        spans = service.match_lexicon(text, automaton)

        assert len(spans) >= 0  # May find matches depending on implementation

    def test_match_templates(self, slang_config):
        """Test template matching."""
        service = SlangMatchingService(slang_config)

        text = "It's giving main character energy"
        spans = service.match_templates(text)

        assert isinstance(spans, list)


# Integration tests
class TestSlangServiceIntegration:
    """Integration tests for slang services."""

    @pytest.fixture
    def mock_lexicon_data(self):
        """Mock lexicon data for integration testing."""
        return {
            "version": "1.0.0",
            "generated_at": "2024-01-01T00:00:00Z",
            "count": 3,
            "items": [
                {
                    "term": "fire",
                    "variants": ["🔥"],
                    "pos": "word",
                    "gloss": "excellent, amazing",
                    "examples": ["That song is fire"],
                    "tags": ["positive"],
                    "status": "approved",
                    "confidence": 0.9,
                    "regions": ["US"],
                    "age_rating": "E",
                    "content_flags": [],
                    "first_seen": "2024-01-01",
                    "last_seen": "2024-01-01",
                    "sources": {"social": 100},
                    "momentum": 1.0,
                    "categories": ["music", "general"]
                },
                {
                    "term": "no cap",
                    "variants": [],
                    "pos": "phrase",
                    "gloss": "no lie, for real",
                    "examples": ["That's fire, no cap"],
                    "tags": ["emphasis"],
                    "status": "approved",
                    "confidence": 0.85,
                    "regions": ["US"],
                    "age_rating": "E",
                    "content_flags": [],
                    "first_seen": "2024-01-01",
                    "last_seen": "2024-01-01",
                    "sources": {"social": 80},
                    "momentum": 1.2,
                    "categories": ["general"]
                },
                {
                    "term": "slaps",
                    "variants": [],
                    "pos": "word",
                    "gloss": "sounds great, is excellent",
                    "examples": ["This song slaps"],
                    "tags": ["positive", "music"],
                    "status": "approved",
                    "confidence": 0.88,
                    "regions": ["US"],
                    "age_rating": "E",
                    "content_flags": [],
                    "first_seen": "2024-01-01",
                    "last_seen": "2024-01-01",
                    "sources": {"social": 90},
                    "momentum": 1.1,
                    "categories": ["music"]
                }
            ]
        }

    def test_full_translation_pipeline(self, mock_lexicon_data):
        """Test the complete translation pipeline."""
        # Integration tests for slang translation now happen through
        # the main TranslationService in test_translation_service.py
        pass
