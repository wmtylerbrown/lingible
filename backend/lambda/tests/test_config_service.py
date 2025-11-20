from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from models.config import AppleConfig, SlangValidationConfig
from utils import config as config_module
from utils.config import ConfigService


def _set_base_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "dev")
    monkeypatch.setenv("APPLE_KEY_ID", "apple-key")
    monkeypatch.setenv("APPLE_ISSUER_ID", "issuer")
    monkeypatch.setenv("APPLE_BUNDLE_ID", "bundle")


def _set_slang_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SLANG_VALIDATION_AUTO_APPROVAL_ENABLED", "true")
    monkeypatch.setenv("SLANG_VALIDATION_AUTO_APPROVAL_THRESHOLD", "0.8")
    monkeypatch.setenv("SLANG_VALIDATION_WEB_SEARCH_ENABLED", "true")
    monkeypatch.setenv("SLANG_VALIDATION_MAX_SEARCH_RESULTS", "3")


def test_apple_config_reads_private_key_from_parameter(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_base_env(monkeypatch)

    captured: dict[str, Any] = {}

    def fake_get_parameter(name: str, decrypt: bool, max_age: int) -> str:
        captured["name"] = name
        captured["decrypt"] = decrypt
        captured["max_age"] = max_age
        return "-----BEGIN PRIVATE KEY-----MOCK-----END PRIVATE KEY-----"

    monkeypatch.setattr(config_module, "get_parameter", fake_get_parameter)

    service = config_module.ConfigService()
    apple_config = service.get_config(AppleConfig)

    assert isinstance(apple_config.private_key, bytes)
    assert apple_config.private_key.decode("utf-8").startswith("-----BEGIN PRIVATE KEY-----")
    assert captured["name"] == "/lingible/dev/secrets/apple-iap-private-key"
    assert captured["decrypt"] is True


def test_slang_validation_config_allows_missing_tavily_key(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_base_env(monkeypatch)
    _set_slang_env(monkeypatch)

    def fake_get_parameter(name: str, decrypt: bool, max_age: int) -> str:
        raise RuntimeError("not found")

    monkeypatch.setattr(config_module, "get_parameter", fake_get_parameter)

    service = config_module.ConfigService()
    slang_config = service.get_config(SlangValidationConfig)

    assert slang_config.tavily_api_key == ""
