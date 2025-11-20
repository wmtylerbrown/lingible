"""Tests for slang models only (no service imports)."""

import pytest
from datetime import datetime, timezone
from decimal import Decimal

from models.slang import (
    SlangTerm,
    SlangLexicon,
    SlangTranslationResponse,
    TranslationSpan,
    LLMValidationResult,
    LLMValidationEvidence,
    SlangSubmission,
    AgeRating,
    AgeFilterMode,
    PartOfSpeech,
    ApprovalStatus,
    SourceType,
    SlangSense,
    SubmissionContext,
)


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

    def test_slang_term_with_senses(self):
        """Test SlangTerm with multiple senses."""
        senses = [
            SlangSense(
                id="sense1",
                gloss="excellent, amazing",
                confidence=0.9,
                examples=["That song is fire"]
            ),
            SlangSense(
                id="sense2",
                gloss="hot, burning",
                confidence=0.7,
                examples=["The fire is hot"]
            )
        ]

        term = SlangTerm(
            term="fire",
            gloss="excellent, amazing",  # Default gloss
            senses=senses,
            first_seen="2024-01-01",
            last_seen="2024-01-01"
        )

        assert term.term == "fire"
        assert len(term.senses) == 2
        assert term.senses[0].gloss == "excellent, amazing"
        assert term.senses[1].gloss == "hot, burning"

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

    def test_translation_span_creation(self):
        """Test TranslationSpan model creation."""
        span = TranslationSpan(
            start=0,
            end=4,
            surface="fire",
            source=SourceType.LEXEME,
            canonical="fire",
            gloss="excellent"
        )

        assert span.start == 0
        assert span.end == 4
        assert span.surface == "fire"
        assert span.source == SourceType.LEXEME
        assert span.canonical == "fire"
        assert span.gloss == "excellent"
        assert span.length == 4

    def test_slang_translation_response_creation(self):
        """Test SlangTranslationResponse model creation."""
        response = SlangTranslationResponse(
            translated="That's excellent",
            confidence=Decimal("0.92"),
            applied_terms=["fire"],
        )

        assert response.translated == "That's excellent"
        assert response.confidence == Decimal("0.92")
        assert response.applied_terms == ["fire"]

    def test_llm_validation_result_creation(self):
        """Test LLMValidationResult model creation."""
        evidence = [
            LLMValidationEvidence(
                source="https://example.com",
                example="That's fire means it's great.",
            )
        ]

        result = LLMValidationResult(
            is_valid=True,
            confidence=Decimal("0.88"),
            evidence=evidence,
            recommended_definition="Excellent or amazing",
            usage_score=8,
            validated_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )

        assert result.is_valid is True
        assert result.confidence == Decimal("0.88")
        assert len(result.evidence) == 1
        assert result.usage_score == 8

    def test_slang_submission_creation(self):
        """Test SlangSubmission model creation."""
        submission = SlangSubmission(
            submission_id="sub_123",
            user_id="user_123",
            slang_term="fire",
            meaning="Excellent, amazing",
            example_usage="That track is fire",
            context=SubmissionContext.MANUAL,
            status=ApprovalStatus.PENDING,
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )

        assert submission.submission_id == "sub_123"
        assert submission.slang_term == "fire"
        assert submission.status == ApprovalStatus.PENDING
        assert submission.context == SubmissionContext.MANUAL

    def test_enum_values(self):
        """Test enum values are correct."""
        # Age ratings
        assert AgeRating.EVERYONE == "E"
        assert AgeRating.TEEN_13 == "T13"
        assert AgeRating.TEEN_16 == "T16"
        assert AgeRating.MATURE_18 == "M18"

        # Age filter modes
        assert AgeFilterMode.SKIP == "skip"
        assert AgeFilterMode.ANNOTATE == "annotate"

        # Parts of speech
        assert PartOfSpeech.PHRASE == "phrase"
        assert PartOfSpeech.WORD == "word"
        assert PartOfSpeech.ABBREVIATION == "abbr"
        assert PartOfSpeech.ACRONYM == "acronym"

        # Approval status
        assert ApprovalStatus.APPROVED == "approved"
        assert ApprovalStatus.PENDING == "pending"
        assert ApprovalStatus.REJECTED == "rejected"
        assert ApprovalStatus.DRAFT == "draft"

        # Source types
        assert SourceType.LEXEME == "lexeme"
        assert SourceType.TEMPLATE == "template"

    def test_model_validation(self):
        """Test model validation works correctly."""
        # Test confidence validation
        with pytest.raises(ValueError):
            SlangTerm(
                term="test",
                gloss="test",
                confidence=1.5,  # Invalid: > 1.0
                first_seen="2024-01-01",
                last_seen="2024-01-01"
            )

        with pytest.raises(ValueError):
            SlangTerm(
                term="test",
                gloss="test",
                confidence=-0.1,  # Invalid: < 0.0
                first_seen="2024-01-01",
                last_seen="2024-01-01"
            )

        # Test span validation
        with pytest.raises(ValueError):
            TranslationSpan(
                start=5,
                end=3,  # Invalid: end < start
                surface="test",
                source=SourceType.LEXEME,
                canonical="test"
            )

    def test_model_serialization(self):
        """Test model serialization to dict."""
        term = SlangTerm(
            term="fire",
            gloss="excellent",
            first_seen="2024-01-01",
            last_seen="2024-01-01"
        )

        data = term.model_dump()
        assert data["term"] == "fire"
        assert data["gloss"] == "excellent"
        assert data["age_rating"] == "E"
        assert data["status"] == "approved"

        # Test deserialization
        term2 = SlangTerm(**data)
        assert term2.term == term.term
        assert term2.gloss == term.gloss
        assert term2.age_rating == term.age_rating
