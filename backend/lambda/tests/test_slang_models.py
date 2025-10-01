"""Tests for slang models only (no service imports)."""

import pytest
from datetime import datetime, timezone

from models.slang import (
    SlangTerm, SlangLexicon, TranslationResult, TranslationSpan,
    QualityMetrics, SlangTranslationResult, SlangTranslationDensity,
    LexiconStats, AgeRating, AgeFilterMode, PartOfSpeech, ApprovalStatus,
    SourceType, SlangSense
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

    def test_translation_result_creation(self):
        """Test TranslationResult model creation."""
        spans = [
            TranslationSpan(
                start=0,
                end=4,
                surface="fire",
                source=SourceType.LEXEME,
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

    def test_lexicon_stats_creation(self):
        """Test LexiconStats model creation."""
        stats = LexiconStats(
            total_terms=100,
            version="1.0.0",
            generated_at="2024-01-01T00:00:00Z",
            age_ratings={"E": 80, "T13": 15, "M18": 5},
            categories={"music": 30, "general": 70},
            confidence_distribution={"high": 60, "medium": 30, "low": 10},
            avg_confidence=0.85
        )

        assert stats.total_terms == 100
        assert stats.version == "1.0.0"
        assert stats.age_ratings["E"] == 80
        assert stats.categories["music"] == 30
        assert stats.avg_confidence == 0.85

    def test_quality_metrics_creation(self):
        """Test QualityMetrics model creation."""
        metrics = QualityMetrics(
            grammar_score=2,
            issues={"repeated_word": 1, "double_punct": 1},
            similarity=0.95,
            bpw_orig=4.5,
            bpw_clean=4.2
        )

        assert metrics.grammar_score == 2
        assert metrics.issues["repeated_word"] == 1
        assert metrics.similarity == 0.95
        assert metrics.bpw_orig == 4.5
        assert metrics.bpw_clean == 4.2

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

        # Translation density
        assert SlangTranslationDensity.LIGHT == "light"
        assert SlangTranslationDensity.MEDIUM == "medium"
        assert SlangTranslationDensity.HEAVY == "heavy"

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
