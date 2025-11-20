from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

import pytest

from models.config import LLMConfig
from models.slang import (
    AgeFilterMode,
    AgeRating,
    SlangTerm,
    TranslationSpan,
    SourceType,
)
from services.slang_matching_service import SlangMatchingService, TranslationSpan as SpanAlias


def _config(age_rating: AgeRating = AgeRating.TEEN_16, filter_mode: AgeFilterMode = AgeFilterMode.SKIP) -> LLMConfig:
    return LLMConfig(
        lexicon_s3_bucket="bucket",
        lexicon_s3_key="key",
        model="model",
        max_tokens=1000,
        temperature=0.5,
        top_p=0.9,
        low_confidence_threshold=0.5,
        age_max_rating=age_rating,
        age_filter_mode=filter_mode,
    )


def _term(
    term: str,
    gloss: str,
    variants: list[str],
    *,
    confidence: float = 0.9,
    age_rating: AgeRating = AgeRating.EVERYONE,
) -> SlangTerm:
    return SlangTerm(
        term=term,
        gloss=gloss,
        variants=variants,
        tags=[],
        examples=[],
        confidence=confidence,
        age_rating=age_rating,
        categories=["social"],
    )


def test_build_automaton_applies_age_filter() -> None:
    service = SlangMatchingService(_config(age_rating=AgeRating.TEEN_13, filter_mode=AgeFilterMode.ANNOTATE))
    terms = [
        _term("rizz", "charisma", ["rizz"]),
        _term("sauce", "style", ["sauce"], age_rating=AgeRating.MATURE_18),
    ]

    automaton = service.build_automaton(terms)
    spans = service.match_lexicon("rizz sauce", automaton)
    assert len(spans) == 2
    assert spans[0].gloss == "charisma"
    assert spans[1].gloss == "[filtered by age]"


def test_match_templates_detects_patterns() -> None:
    service = SlangMatchingService(_config())
    spans = service.match_templates("it's giving main character energy and barbiecore aesthetic vibes, soft-pilled")
    canonical = {span.canonical for span in spans}
    assert "it's giving" in canonical
    assert "-core" in canonical
    assert "X aesthetic" in canonical
    assert "-pilled" in canonical


def test_resolve_overlaps_prefers_non_overlapping() -> None:
    service = SlangMatchingService(_config())
    span1 = TranslationSpan(
        start=0,
        end=4,
        surface="word",
        source=SourceType.LEXEME,
        canonical="word",
        gloss="g",
        confidence=0.9,
        meta={},
    )
    span2 = TranslationSpan(
        start=2,
        end=6,
        surface="ordx",
        source=SourceType.TEMPLATE,
        canonical="template",
        gloss="t",
        confidence=0.8,
        meta={},
    )
    result = service.resolve_overlaps([span2, span1])
    assert result[0] == span1


def test_match_variant_fallbacks_returns_soft_matches() -> None:
    service = SlangMatchingService(_config())
    chosen = [
        TranslationSpan(
            start=0,
            end=4,
            surface="rizz",
            source=SourceType.LEXEME,
            canonical="rizz",
            gloss="charisma",
            confidence=0.9,
            meta={},
        )
    ]
    term = _term("yeet", "throw forcefully", ["yeet", "yeeted"])
    variant_index = {"yeet": [(term, "yeet", 0.8)]}
    spans = service.match_variant_fallbacks("rizz yeet", chosen, variant_index)
    assert spans[0].canonical == "yeet"


def test_match_variant_fallbacks_respects_age_filter() -> None:
    service = SlangMatchingService(_config(age_rating=AgeRating.TEEN_13, filter_mode=AgeFilterMode.ANNOTATE))
    term = _term("mature", "gloss", ["mature"], age_rating=AgeRating.MATURE_18)
    spans = service.match_variant_fallbacks(
        "mature",
        [],
        {"mature": [(term, "mature", 0.5)]},
    )
    assert spans[0].meta["filtered"] is True


def test_normalization_helpers() -> None:
    service = SlangMatchingService(_config())
    assert service._normalize_token("R1ZZ") == "rizz"
    assert service._split_hashtag("#MainCharacterEnergy") == "main character energy"
