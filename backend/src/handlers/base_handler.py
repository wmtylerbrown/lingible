"""Base Lambda handler with enhanced error handling and request tracking."""

import time
import uuid
from typing import Dict, Any, Optional
from aws_lambda_powertools.utilities.typing import LambdaContext

from ..models.aws import APIGatewayResponse, CognitoUserInfo
from aws_lambda_powertools.utilities.parser.models import (
    APIGatewayProxyEventModel as APIGatewayEvent,
)
from ..utils.cognito import cognito_extractor
from ..utils.logging import logger
from ..utils.tracing import tracer
from ..utils.config import get_config
from ..utils.response import (
    create_success_response,
    create_error_response,
    create_internal_error_response,
    response_to_dict,
)
from ..utils.exceptions import AppException, AuthenticationError, ValidationError

# Get configuration
config = get_config()


class BaseHandler:
    """Base Lambda handler with comprehensive error handling and request tracking."""

    def __init__(self) -> None:
        """Initialize base handler."""
        self.request_id: Optional[str] = None
        self.start_time: Optional[float] = None

    def handle(self, event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
        """Main handler method with comprehensive error handling."""
        try:
            # Generate request ID for tracing
            self.request_id = str(uuid.uuid4())
            self.start_time = time.time()

            # Parse and validate event
            api_event = APIGatewayEvent.model_validate(event)

            # Log request
            self.log_request(api_event)

            # Process the request
            result = self.process_request(api_event, context)

            # Create success response
            response = create_success_response(
                message="Request processed successfully", data=result
            )

            # Log response
            duration_ms = (time.time() - self.start_time) * 1000
            self.log_response(response, duration_ms)

            return response_to_dict(response)

        except AppException as e:
            # Handle application-specific exceptions
            e.request_id = self.request_id
            response = create_error_response(e, self.request_id)
            duration_ms = (
                (time.time() - self.start_time) * 1000 if self.start_time else 0
            )
            self.log_response(response, duration_ms)
            return response_to_dict(response)

        except Exception as e:
            # Handle unexpected exceptions
            logger.log_error(e, {"request_id": self.request_id})
            response = create_internal_error_response(
                message="An unexpected error occurred", request_id=self.request_id
            )
            duration_ms = (
                (time.time() - self.start_time) * 1000 if self.start_time else 0
            )
            self.log_response(response, duration_ms)
            return response_to_dict(response)

    def process_request(
        self, event: APIGatewayEvent, context: LambdaContext
    ) -> Dict[str, Any]:
        """Process the actual request. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement process_request")

    def get_user_from_event(self, event: APIGatewayEvent) -> Optional[CognitoUserInfo]:
        """Extract user information from API Gateway event."""
        return cognito_extractor.extract_user_from_event(event)

    def require_authentication(self, event: APIGatewayEvent) -> CognitoUserInfo:
        """Require authentication and return user info. Raises AuthenticationError if not authenticated."""
        user = self.get_user_from_event(event)
        if not user:
            raise AuthenticationError(
                message="Authentication required",
                details={"request_id": self.request_id},
            )
        return user

    def validate_required_fields(
        self, data: Dict[str, Any], required_fields: list[str]
    ) -> None:
        """Validate that required fields are present in request data."""
        missing_fields = [
            field
            for field in required_fields
            if field not in data or data[field] is None
        ]
        if missing_fields:
            raise ValidationError(
                message=f"Missing required fields: {', '.join(missing_fields)}",
                details={"missing_fields": missing_fields},
            )

    def log_request(self, event: APIGatewayEvent) -> None:
        """Log incoming request with request ID."""
        log_data = {
            "request_id": self.request_id,
            "http_method": event.httpMethod,
            "path": event.path,
            "query_params": event.queryStringParameters,
            "path_params": event.pathParameters,
            "headers": self._sanitize_headers(event.headers or {}),
        }

        logger.logger.info("Incoming request", extra=log_data)

    def log_response(
        self, response: Dict[str, Any] | APIGatewayResponse, duration_ms: float
    ) -> None:
        """Log response with performance metrics."""
        if isinstance(response, APIGatewayResponse):
            status_code = response.statusCode
            body = response.body
        else:
            status_code = response.get("statusCode", 200)
            body = response.get("body", "")

        log_data = {
            "request_id": self.request_id,
            "status_code": status_code,
            "duration_ms": duration_ms,
            "response_size": len(body),
        }

        logger.logger.info("Response sent", extra=log_data)

    def _sanitize_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Remove sensitive data from headers."""
        sensitive_fields = config.get_security_config()["sensitive_fields"]
        sanitized = headers.copy()
        for field in sensitive_fields:
            if field.lower() in sanitized:
                sanitized[field.lower()] = "[REDACTED]"
        return sanitized

    @tracer.trace_method("handler_method")
    def trace_method(self, method_name: str = ""):
        """Decorator to trace method execution."""
        return tracer.trace_method(method_name)
