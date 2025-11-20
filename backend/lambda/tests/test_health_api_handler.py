"""Tests for health API handler."""

import json
import importlib

import pytest


class TestHealthAPIHandler:
    """Test health API handler."""

    @pytest.fixture
    def module(self):
        return importlib.import_module("handlers.health_api.handler")

    @pytest.fixture
    def handler(self, module):
        return module.handler

    def test_health_check_success(self, handler, minimal_api_gateway_event):
        """Test successful health check."""
        context = {}

        response = handler(minimal_api_gateway_event, context)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["status"] == "healthy"
