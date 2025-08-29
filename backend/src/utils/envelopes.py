"""Base envelope classes for Lambda handlers."""

from __future__ import annotations
from typing import Any, Dict, TypeVar, TYPE_CHECKING
from aws_lambda_powertools.utilities.parser import BaseEnvelope
from aws_lambda_powertools.utilities.parser.models import APIGatewayProxyEventModel
from pydantic import BaseModel

from ..models.translations import TranslationRequest
from ..models.subscriptions import UserUpgradeRequest, AppleWebhookRequest


if TYPE_CHECKING:
    T = TypeVar("T", bound=BaseModel)
else:
    T = TypeVar("T")


class APIGatewayEnvelope(BaseEnvelope):
    """Base envelope specifically for API Gateway events with full type safety."""

    def parse(self, data: Any, model: Any) -> Dict[str, Any]:
        """Parse API Gateway event with type checking."""
        # Ensure data is a dict for API Gateway events
        if not isinstance(data, dict):
            raise ValueError("Expected dict for API Gateway event")

        # Parse the API Gateway event
        event = APIGatewayProxyEventModel(**data)

        # Extract common API Gateway data
        base_data = self._extract_common_data(event)

        # Let subclasses add their specific parsing logic
        return self._parse_api_gateway(event, model, base_data)

    def _extract_common_data(self, event: APIGatewayProxyEventModel) -> Dict[str, Any]:
        """Extract common data from API Gateway event."""
        # Extract user info from authorizer context (set by API Gateway authorizer)
        user_id = None
        username = None

        if event.requestContext and event.requestContext.authorizer:
            authorizer_context = event.requestContext.authorizer
            # Access authorizer context as a dictionary
            user_id = getattr(authorizer_context, "user_id", None)
            username = getattr(authorizer_context, "username", None)

        # Get request metadata
        request_id = event.requestContext.requestId if event.requestContext else None

        return {
            "event": event.model_dump(),
            "user_id": user_id,
            "username": username,
            "request_id": request_id,
        }

    def _parse_api_gateway(
        self,
        event: APIGatewayProxyEventModel,
        model: type[T],
        base_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Override this method in subclasses to add handler-specific parsing."""
        raise NotImplementedError("Subclasses must implement _parse_api_gateway")


class AuthenticatedAPIGatewayEnvelope(APIGatewayEnvelope):
    """Base envelope for authenticated API Gateway events."""

    def _extract_common_data(self, event: APIGatewayProxyEventModel) -> Dict[str, Any]:
        """Extract common data from API Gateway event with authentication validation."""
        # Extract user info from authorizer context (set by API Gateway authorizer)
        user_id = None
        username = None

        if event.requestContext and event.requestContext.authorizer:
            authorizer_context = event.requestContext.authorizer
            user_id = getattr(authorizer_context, "user_id", None)
            username = getattr(authorizer_context, "username", None)

        # Validate authentication for protected endpoints
        if not user_id:
            raise ValueError("Valid authentication token is required for this endpoint")

        # Get request metadata
        request_id = event.requestContext.requestId if event.requestContext else None

        return {
            "event": event.model_dump(),
            "user_id": user_id,
            "username": username,
            "request_id": request_id,
        }


class TranslationEnvelope(AuthenticatedAPIGatewayEnvelope):
    """Envelope for translation endpoints that parses request body."""

    def _parse_api_gateway(
        self,
        event: APIGatewayProxyEventModel,
        model: type[T],
        base_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Parse translation-specific data."""
        # Parse the request body
        if not event.body:
            raise ValueError("Request body is required")

        request_body = TranslationRequest.model_validate_json(str(event.body))

        # Add translation-specific data
        base_data["request_body"] = request_body

        return base_data


class UserProfileEnvelope(AuthenticatedAPIGatewayEnvelope):
    """Envelope for user profile endpoints."""

    def _parse_api_gateway(
        self,
        event: APIGatewayProxyEventModel,
        model: type[T],
        base_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Parse user profile-specific data."""
        # For user profile endpoints, we rely on the authorizer context
        return base_data


class TranslationHistoryEnvelope(APIGatewayEnvelope):
    """Envelope for translation history endpoints that parses query parameters."""

    def _parse_api_gateway(
        self,
        event: APIGatewayProxyEventModel,
        model: type[T],
        base_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Parse translation history-specific data."""
        # Extract query parameters
        query_params = event.queryStringParameters or {}

        # Parse pagination parameters
        limit = int(query_params.get("limit", "10"))
        offset = int(query_params.get("offset", "0"))

        # Validate limits
        if limit < 1 or limit > 100:
            limit = 10
        if offset < 0:
            offset = 0

        # Add history-specific data
        base_data.update(
            {
                "limit": limit,
                "offset": offset,
            }
        )

        return base_data


class UserUsageEnvelope(AuthenticatedAPIGatewayEnvelope):
    """Envelope for user usage endpoints that extracts user info."""

    def _parse_api_gateway(
        self,
        event: APIGatewayProxyEventModel,
        model: type[T],
        base_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Parse user usage specific data."""
        # For GET requests, we don't need to parse a request body
        # Just return the base data with user info
        return base_data


class HealthEnvelope(APIGatewayEnvelope):
    """Envelope for health check endpoints."""

    def _parse_api_gateway(
        self,
        event: APIGatewayProxyEventModel,
        model: type[T],
        base_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Parse health check specific data."""
        return base_data


class SubscriptionEnvelope(AuthenticatedAPIGatewayEnvelope):
    """Envelope for subscription endpoints that extracts user info."""

    def _parse_api_gateway(
        self,
        event: APIGatewayProxyEventModel,
        model: type[T],
        base_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Parse subscription-specific data."""
        # For subscription endpoints, we extract user info from authorizer context
        # and handle path parameters for specific subscription operations
        return base_data


class UserUpgradeEnvelope(AuthenticatedAPIGatewayEnvelope):
    """Envelope for user upgrade endpoints that parses request body."""

    def _parse_api_gateway(
        self,
        event: APIGatewayProxyEventModel,
        model: type[T],
        base_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Parse user upgrade specific data."""
        # Parse the request body
        if not event.body:
            raise ValueError("Request body is required")

        # Parse and validate the request body
        request_body = UserUpgradeRequest.model_validate_json(str(event.body))

        # Add upgrade-specific data
        base_data["request_body"] = request_body

        return base_data


class WebhookEnvelope(APIGatewayEnvelope):
    """Envelope for webhook endpoints that parses request body."""

    def _parse_api_gateway(
        self,
        event: APIGatewayProxyEventModel,
        model: type[T],
        base_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Parse webhook specific data."""
        # Parse the request body
        if not event.body:
            raise ValueError("Request body is required")

        # Parse and validate the request body
        request_body = AppleWebhookRequest.model_validate_json(str(event.body))

        # Add webhook-specific data
        base_data["request_body"] = request_body

        return base_data


# Backward compatibility - keep the old name for existing code
BaseAuthenticatedEnvelope = APIGatewayEnvelope
