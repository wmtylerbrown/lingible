from __future__ import annotations

import io
import json
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from models.config import LLMConfig
from models.slang import AgeFilterMode, AgeRating, SlangTranslationResponse, TranslationSpan, SourceType
from services.slang_llm_service import SlangLLMService


def _config() -> LLMConfig:
    return LLMConfig(
        lexicon_s3_bucket="bucket",
        lexicon_s3_key="key",
        model="anthropic.model",
        max_tokens=500,
        temperature=0.2,
        top_p=0.9,
        low_confidence_threshold=0.5,
        age_max_rating=AgeRating.EVERYONE,
        age_filter_mode=AgeFilterMode.SKIP,
    )


def _bedrock_payload(text: str) -> bytes:
    return json.dumps({"content": [{"text": text}]}).encode("utf-8")


@pytest.fixture
def mock_bedrock():
    with patch("services.slang_llm_service.aws_services") as aws_services_mock:
        client = aws_services_mock.bedrock_client
        yield aws_services_mock, client


def test_translate_with_context_success(mock_bedrock) -> None:
    aws_services_mock, bedrock_client = mock_bedrock
    response_text = json.dumps(
        {"clean_text": "translated", "applied_terms": ["term"], "confidence": 0.9}
    )
    bedrock_client.invoke_model.return_value = {
        "body": io.BytesIO(_bedrock_payload(response_text))
    }

    service = SlangLLMService(_config())
    span = TranslationSpan(
        start=0,
        end=4,
        surface="rizz",
        canonical="rizz",
        gloss="charisma",
        source=SourceType.LEXEME,
        meta={},
    )
    result = service.translate_with_context("rizz", [span])

    assert result.translated == "translated"
    bedrock_client.invoke_model.assert_called_once()


def test_translate_with_context_fallback_on_error(mock_bedrock) -> None:
    aws_services_mock, bedrock_client = mock_bedrock
    bedrock_client.invoke_model.side_effect = RuntimeError("boom")

    service = SlangLLMService(_config())
    span = TranslationSpan(
        start=0,
        end=4,
        surface="rizz",
        canonical="rizz",
        gloss="charisma",
        source=SourceType.LEXEME,
        meta={},
    )
    result = service.translate_with_context("rizz", [span])

    assert "charisma" in result.translated
    assert result.confidence == Decimal("0.3")


def test_translate_to_genz_returns_original_on_error(mock_bedrock) -> None:
    aws_services_mock, bedrock_client = mock_bedrock
    bedrock_client.invoke_model.side_effect = RuntimeError("boom")
    service = SlangLLMService(_config())

    result = service.translate_to_genz("hello")
    assert result.translated == "hello"
    assert result.confidence == Decimal("0.1")


def test_parse_llm_response_handles_markdown(mock_bedrock) -> None:
    aws_services_mock, bedrock_client = mock_bedrock
    response_text = """```json
{"clean_text":"sup","applied_terms":["term"],"confidence":0.8}
```"""
    bedrock_client.invoke_model.return_value = {
        "body": io.BytesIO(_bedrock_payload(response_text))
    }

    service = SlangLLMService(_config())
    span = TranslationSpan(
        start=0,
        end=4,
        surface="word",
        canonical="word",
        gloss=None,
        source=SourceType.LEXEME,
        meta={},
    )
    result = service.translate_with_context("word", [span])
    assert result.translated == "sup"


def test_parse_llm_response_handles_invalid_json(mock_bedrock) -> None:
    aws_services_mock, bedrock_client = mock_bedrock
    bedrock_client.invoke_model.return_value = {
        "body": io.BytesIO(_bedrock_payload("not-json"))
    }

    service = SlangLLMService(_config())
    span = TranslationSpan(
        start=0,
        end=4,
        surface="word",
        canonical="word",
        gloss=None,
        source=SourceType.LEXEME,
        meta={},
    )
    result = service.translate_with_context("word", [span])
    assert result.translated == "not-json"
    assert result.confidence == Decimal("0.3")


def test_fallback_translation_no_spans(mock_bedrock) -> None:
    aws_services_mock, bedrock_client = mock_bedrock
    bedrock_client.invoke_model.side_effect = RuntimeError("boom")
    service = SlangLLMService(_config())
    result = service.translate_with_context("text", [])
    assert result.translated == "text"


def test_call_bedrock_uses_config(mock_bedrock) -> None:
    aws_services_mock, bedrock_client = mock_bedrock
    bedrock_client.invoke_model.return_value = {
        "body": io.BytesIO(_bedrock_payload('{"clean_text":"ok","applied_terms":[],"confidence":0.9}'))
    }
    service = SlangLLMService(_config())
    prompt = service._create_english_to_genz_prompt("hello")
    service._call_bedrock(prompt)
    bedrock_client.invoke_model.assert_called_once()
