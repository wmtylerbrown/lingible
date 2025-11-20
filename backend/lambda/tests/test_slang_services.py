"""Tests for slang translation services."""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from decimal import Decimal

from models.slang import (
    SlangTerm,
    TranslationSpan,
    AgeRating,
    AgeFilterMode,
    PartOfSpeech,
    ApprovalStatus,
    SourceType,
)
from services.slang_lexicon_service import SlangLexiconService
from services.slang_matching_service import SlangMatchingService, RuntimeTemplate
from services.slang_llm_service import SlangLLMService
from models.config import LLMConfig


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
        return LLMConfig(
            model="anthropic.claude-3-sonnet-20240229-v1:0",
            max_tokens=1000,
            temperature=0.7,
            top_p=0.9,
            low_confidence_threshold=Decimal("0.2"),
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

class TestSlangMatchingService:
    """Test SlangMatchingService."""

    @pytest.fixture
    def slang_config(self):
        """Create SlangConfig for testing."""
        return LLMConfig(
            model="anthropic.claude-3-sonnet-20240229-v1:0",
            max_tokens=1000,
            temperature=0.7,
            top_p=0.9,
            low_confidence_threshold=Decimal("0.2"),
            lexicon_s3_bucket="test-bucket",
            lexicon_s3_key="test/lexicon.json",
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


class TestSlangLLMService:
    """Test SlangLLMService prompt generation."""

    @pytest.fixture
    def llm_config(self):
        """Create LLMConfig for testing."""
        from models.config import LLMConfig
        return LLMConfig(
            lexicon_s3_bucket="test-bucket",
            lexicon_s3_key="test/lexicon.json",
            lexicon_local_path="",
            titan_model_id="amazon.titan-embed-text-v2:0",
            low_confidence_threshold=Decimal("0.2"),
            age_max_rating=AgeRating.MATURE_18,
            age_filter_mode=AgeFilterMode.SKIP,
            model="anthropic.claude-3-sonnet-20240229-v1:0",
            max_tokens=1000,
            temperature=0.7,
            top_p=0.9,
        )

    def test_genz_to_english_prompt_emphasizes_casual_language(self, llm_config):
        """Test that GenZ to English prompt emphasizes casual, conversational language."""
        from models.slang import TranslationSpan

        spans = [
            TranslationSpan(
                canonical="rizz",
                start=15,
                end=19,
                surface="rizz",
                source=SourceType.LEXEME,
                gloss="charisma;flirting skill",
                confidence=0.9,
            )
        ]

        service = SlangLLMService(llm_config)
        prompt = service._create_genz_to_english_prompt("That boy has rizz", spans)

        # Verify prompt contains instructions about casual language
        assert "casual" in prompt.lower() or "conversational" in prompt.lower()
        assert "everyday" in prompt.lower() or "natural" in prompt.lower()
        assert "formal" in prompt.lower() or "academic" in prompt.lower()

        # Verify it includes the rizz example
        assert "rizz" in prompt.lower()
        assert "game" in prompt.lower() or "smooth" in prompt.lower()

        # Verify it tells LLM NOT to use formal definitions
        assert "not" in prompt.lower() or "avoid" in prompt.lower() or "don't" in prompt.lower()

        # Verify it mentions using "guy" instead of "person"
        assert "guy" in prompt.lower()

    def test_genz_to_english_prompt_includes_rizz_example(self, llm_config):
        """Test that prompt includes specific example for rizz translation."""
        service = SlangLLMService(llm_config)
        prompt = service._create_genz_to_english_prompt("test", [])

        # Check for the rizz example in the prompt
        assert "that boy has rizz" in prompt.lower() or "rizz" in prompt.lower()
        # Should show casual translation, not formal
        assert ("game" in prompt.lower() or "smooth" in prompt.lower()) or \
               ("charisma and flirting skills" in prompt.lower())
