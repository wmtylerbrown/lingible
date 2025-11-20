"""Tests for envelope classes."""

import pytest

from utils.envelopes import (
    TranslationEnvelope,
    SimpleAuthenticatedEnvelope,
    PathParameterEnvelope,
    TranslationHistoryEnvelope,
)
from utils.exceptions import AuthenticationError
from models.events import (
    TranslationEvent,
    SimpleAuthenticatedEvent,
    PathParameterEvent,
    TranslationHistoryEvent,
)


class TestEnvelopes:
    """Test envelope classes."""

    def test_authenticated_api_gateway_envelope(self, authenticated_api_gateway_event):
        """Test AuthenticatedAPIGatewayEnvelope."""
        event = authenticated_api_gateway_event.copy()
        event["requestContext"]["authorizer"]["claims"]["sub"] = "test_user_123"
        event["requestContext"]["authorizer"]["claims"]["email"] = "test@example.com"

        envelope = SimpleAuthenticatedEnvelope()
        parsed_event = envelope.parse(event, SimpleAuthenticatedEvent)

        assert parsed_event.user_id == "test_user_123"
        assert parsed_event.request_id == "test-request-id"

    def test_translation_envelope(self, api_gateway_event_with_body):
        """Test TranslationEnvelope."""
        event = api_gateway_event_with_body.copy()
        event["requestContext"]["authorizer"]["claims"]["sub"] = "test_user_123"
        event["body"] = '{"text": "Hello world", "direction": "english_to_genz"}'

        envelope = TranslationEnvelope()
        parsed_event = envelope.parse(event, TranslationEvent)

        assert parsed_event.user_id == "test_user_123"
        assert parsed_event.request_body.text == "Hello world"
        assert parsed_event.request_body.direction.value == "english_to_genz"

    def test_translation_history_envelope(self, api_gateway_event_with_query_params):
        """Test TranslationHistoryEnvelope."""
        event = api_gateway_event_with_query_params.copy()
        event["requestContext"]["authorizer"]["claims"]["sub"] = "test_user_123"
        event["queryStringParameters"] = {"limit": "10", "offset": "0"}
        event["multiValueQueryStringParameters"] = {"limit": ["10"], "offset": ["0"]}

        envelope = TranslationHistoryEnvelope()
        parsed_event = envelope.parse(event, TranslationHistoryEvent)

        assert parsed_event.user_id == "test_user_123"
        assert parsed_event.limit == 10
        assert parsed_event.offset == 0

    def test_simple_authenticated_envelope(self, authenticated_api_gateway_event):
        """Test SimpleAuthenticatedEnvelope."""
        event = authenticated_api_gateway_event.copy()
        event["requestContext"]["authorizer"]["claims"]["sub"] = "test_user_123"

        envelope = SimpleAuthenticatedEnvelope()
        parsed_event = envelope.parse(event, SimpleAuthenticatedEvent)

        assert parsed_event.user_id == "test_user_123"

    def test_path_parameter_envelope(self, api_gateway_event_with_path_params):
        """Test PathParameterEnvelope."""
        event = api_gateway_event_with_path_params.copy()
        event["requestContext"]["authorizer"]["claims"]["sub"] = "test_user_123"
        event["pathParameters"]["translation_id"] = "trans_789"

        envelope = PathParameterEnvelope()
        parsed_event = envelope.parse(event, PathParameterEvent)

        assert parsed_event.user_id == "test_user_123"
        assert parsed_event.path_parameters["translation_id"] == "trans_789"

    def test_envelope_missing_authorizer(self, minimal_api_gateway_event):
        """Test envelope with missing authorizer raises error."""
        event = minimal_api_gateway_event.copy()
        # Ensure authorizer doesn't exist to trigger error
        if "authorizer" in event.get("requestContext", {}):
            del event["requestContext"]["authorizer"]

        envelope = SimpleAuthenticatedEnvelope()

        with pytest.raises(AuthenticationError):
            envelope.parse(event, SimpleAuthenticatedEvent)

    def test_envelope_missing_user_id(self, authenticated_api_gateway_event):
        """Test envelope with missing user_id raises error."""
        event = authenticated_api_gateway_event.copy()
        # Set 'sub' field to empty string to trigger authentication error
        # (We can't delete it because the event model requires it)
        event["requestContext"]["authorizer"]["claims"]["sub"] = ""

        envelope = SimpleAuthenticatedEnvelope()

        with pytest.raises(AuthenticationError):
            envelope.parse(event, SimpleAuthenticatedEvent)
