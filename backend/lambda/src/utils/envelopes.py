"""Envelope classes for parsing Lambda events."""

from __future__ import annotations
from typing import Any, Dict, TypeVar, TYPE_CHECKING
from aws_lambda_powertools.utilities.parser import BaseEnvelope
from pydantic import BaseModel

from models.translations import TranslationRequest
from models.subscriptions import UserUpgradeRequest, AppleWebhookRequest
from models.events import CustomAPIGatewayProxyEventModel
from .exceptions import ValidationError, AuthenticationError

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
            raise ValidationError("Expected dict for API Gateway event")

        # Parse the API Gateway event with our custom model
        event = CustomAPIGatewayProxyEventModel(**data)

        # Extract common API Gateway data
        base_data = self._extract_common_data(event)

        # Let subclasses add their specific parsing logic
        result = self._parse_api_gateway(event, model, base_data)

        # Return the model instance instead of the dictionary
        return model(**result)

    def _extract_common_data(self, event: CustomAPIGatewayProxyEventModel) -> Dict[str, Any]:
        """Extract common data from API Gateway event."""
        # Extract user info from authorizer context (set by API Gateway authorizer)
        user_id = None
        username = None

        if event.requestContext and event.requestContext.authorizer:
            authorizer_context = event.requestContext.authorizer
            # Access authorizer context as a dictionary
            user_id = getattr(authorizer_context, "user_id", None)
            username = getattr(authorizer_context, "username", None)

        # Get request metadata (API Gateway always provides requestContext)
        if not event.requestContext:
            raise ValidationError("Invalid API Gateway event: missing requestContext")

        request_id = event.requestContext.requestId
        if not request_id:
            raise ValidationError("Invalid API Gateway event: missing requestId")

        return {
            "event": event.model_dump(),
            "user_id": user_id,
            "username": username,
            "request_id": request_id,
        }

    def _parse_api_gateway(
        self,
        event: CustomAPIGatewayProxyEventModel,
        model: type[T],
        base_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Override this method in subclasses to add handler-specific parsing."""
        raise NotImplementedError("Subclasses must implement _parse_api_gateway")


class AuthenticatedAPIGatewayEnvelope(APIGatewayEnvelope):
    """Base envelope for authenticated API Gateway events."""

    def _extract_common_data(self, event: CustomAPIGatewayProxyEventModel) -> Dict[str, Any]:
        """Extract common data from API Gateway event with authentication validation."""
        # Extract user info from authorizer context (set by API Gateway authorizer)
        user_id = None
        username = None

        if event.requestContext and event.requestContext.authorizer:
            authorizer_context = event.requestContext.authorizer
            # Access authorizer context as a dictionary
            user_id = getattr(authorizer_context, "user_id", None)
            username = getattr(authorizer_context, "username", None)

        # Validate authentication for protected endpoints
        if not user_id:
            raise AuthenticationError(
                "Valid authentication token is required for this endpoint"
            )

        # Ensure username is provided (fallback to user_id if not available)
        if not username:
            username = user_id

        # Get request metadata (API Gateway always provides requestContext)
        if not event.requestContext:
            raise ValidationError("Invalid API Gateway event: missing requestContext")

        request_id = event.requestContext.requestId
        if not request_id:
            raise ValidationError("Invalid API Gateway event: missing requestId")

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
        event: CustomAPIGatewayProxyEventModel,
        model: type[T],
        base_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Parse translation-specific data."""
        # Parse the request body
        if not event.body:
            raise ValidationError("Request body is required")

        request_body = TranslationRequest.model_validate_json(str(event.body))

        # Add translation-specific data
        base_data["request_body"] = request_body

        return base_data


class UserUpgradeEnvelope(AuthenticatedAPIGatewayEnvelope):
    """Envelope for user upgrade endpoints that parses request body."""

    def _parse_api_gateway(
        self,
        event: CustomAPIGatewayProxyEventModel,
        model: type[T],
        base_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Parse user upgrade specific data."""
        # Parse the request body
        if not event.body:
            raise ValidationError("Request body is required")

        # Parse and validate the request body
        request_body = UserUpgradeRequest.model_validate_json(str(event.body))

        # Add upgrade-specific data
        base_data["request_body"] = request_body

        return base_data


class SimpleEnvelope(APIGatewayEnvelope):
    """Simple envelope for basic operations (GET)"""

    def _parse_api_gateway(
        self,
        event: CustomAPIGatewayProxyEventModel,
        model: type[T],
        base_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Parse data."""
        return base_data


class SimpleAuthenticatedEnvelope(AuthenticatedAPIGatewayEnvelope):
    """Simple envelope for basic authenticated operations (GET, DELETE) that only need user info."""

    def _parse_api_gateway(
        self,
        event: CustomAPIGatewayProxyEventModel,
        model: type[T],
        base_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Parse simple authenticated data - just return base data with user info."""
        return base_data


class PathParameterEnvelope(AuthenticatedAPIGatewayEnvelope):
    """Envelope for operations that need path parameters (DELETE /{id}, etc.)."""

    def _parse_api_gateway(
        self,
        event: CustomAPIGatewayProxyEventModel,
        model: type[T],
        base_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Parse path parameters and add them to base data."""
        # Extract path parameters
        if event.pathParameters:
            base_data["path_parameters"] = event.pathParameters
        else:
            base_data["path_parameters"] = {}

        return base_data


class TranslationHistoryEnvelope(AuthenticatedAPIGatewayEnvelope):
    """Envelope for translation history endpoints that extracts query parameters."""

    def _parse_api_gateway(
        self,
        event: CustomAPIGatewayProxyEventModel,
        model: type[T],
        base_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Parse translation history specific data."""
        # Extract query parameters for pagination
        if event.queryStringParameters:
            try:
                limit = int(event.queryStringParameters.get("limit", "20"))
                base_data["limit"] = limit
            except ValueError:
                base_data["limit"] = 20

            base_data["last_evaluated_key"] = event.queryStringParameters.get(
                "last_evaluated_key"
            )
        else:
            base_data["limit"] = 20
            base_data["last_evaluated_key"] = None

        return base_data


class AccountDeletionEnvelope(AuthenticatedAPIGatewayEnvelope):
    """Envelope for account deletion endpoints that parses request body."""

    def _parse_api_gateway(
        self,
        event: CustomAPIGatewayProxyEventModel,
        model: type[T],
        base_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Parse account deletion specific data."""
        # Parse the request body
        if not event.body:
            raise ValidationError("Request body is required")

        # Import here to avoid circular imports
        from models.users import AccountDeletionRequest

        # Parse and validate the request body
        request_body = AccountDeletionRequest.model_validate_json(str(event.body))

        # Add account deletion-specific data
        base_data["request_body"] = request_body

        return base_data


class WebhookEnvelope(APIGatewayEnvelope):
    """Envelope for webhook endpoints that parses request body."""

    def _parse_api_gateway(
        self,
        event: CustomAPIGatewayProxyEventModel,
        model: type[T],
        base_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Parse webhook specific data."""
        # Parse the request body
        if not event.body:
            raise ValidationError("Request body is required")

        # Parse and validate the request body
        request_body = AppleWebhookRequest.model_validate_json(str(event.body))

        # Add webhook-specific data
        base_data["request_body"] = request_body

        return base_data
