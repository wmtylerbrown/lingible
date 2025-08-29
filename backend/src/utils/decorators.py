"""Decorators for Lambda handlers."""

import functools
from typing import Callable, Any, Dict, Optional
from pydantic import BaseModel

from ..models.aws import APIGatewayResponse
from ..utils.logging import logger
from ..utils.response import (
    create_validation_error_response,
    create_unauthorized_response,
    create_rate_limit_response,
    create_internal_error_response,
    create_model_response,
)
from ..utils.exceptions import (
    ValidationError,
    AuthenticationError,
    RateLimitExceededError,
    BusinessLogicError,
    SystemError,
)


def handle_errors(
    user_id: Optional[str] = None,
    extract_user_id: Optional[Callable[[Any], str]] = None,
) -> Callable:
    """
    Decorator to handle common errors in Lambda handlers and automatically create API responses.

    Args:
        user_id: Static user ID to use for logging (if known)
        extract_user_id: Function to extract user ID from handler arguments

    Returns:
        Decorated function with comprehensive error handling and automatic response creation
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> APIGatewayResponse:
            # Extract user ID for logging
            current_user_id = user_id
            if extract_user_id and not current_user_id:
                try:
                    # Try to extract user ID from the first argument (usually parsed_data or event)
                    current_user_id = extract_user_id(args[0] if args else None)
                except Exception:
                    current_user_id = "unknown"

            try:
                # Execute the handler function
                result = func(*args, **kwargs)

                # If the result is already an APIGatewayResponse, return it as-is
                if isinstance(result, APIGatewayResponse):
                    return result

                # If the result is a Pydantic model, create a success response
                if isinstance(result, BaseModel):
                    return create_model_response(result)

                # If the result is a tuple of (message, model), use the custom message
                if isinstance(result, tuple) and len(result) == 2:
                    message, model = result
                    if isinstance(model, BaseModel):
                        return create_model_response(model)

                # For any other result type, return as-is (backward compatibility)
                return result

            except ValidationError as e:
                logger.log_error(
                    e, {"user_id": current_user_id, "error_type": "validation"}
                )
                return create_validation_error_response(str(e))

            except AuthenticationError as e:
                logger.log_error(
                    e, {"user_id": current_user_id, "error_type": "authentication"}
                )
                return create_unauthorized_response(str(e))

            except RateLimitExceededError as e:
                logger.log_error(
                    e, {"user_id": current_user_id, "error_type": "rate_limit"}
                )
                return create_rate_limit_response(100, 3600)  # Default rate limit

            except BusinessLogicError as e:
                logger.log_error(
                    e, {"user_id": current_user_id, "error_type": "business_logic"}
                )
                return create_internal_error_response(str(e))

            except SystemError as e:
                logger.log_error(
                    e, {"user_id": current_user_id, "error_type": "system"}
                )
                return create_internal_error_response(str(e))

            except Exception as e:
                logger.log_error(
                    e, {"user_id": current_user_id, "error_type": "unknown"}
                )
                return create_internal_error_response("An unexpected error occurred")

        return wrapper

    return decorator


def extract_user_from_parsed_data(parsed_data: Dict[str, Any]) -> str:
    """Extract user ID from parsed data containing event."""
    try:
        if isinstance(parsed_data, dict) and "event" in parsed_data:
            # For handlers using custom envelopes
            event = parsed_data["event"]
            if hasattr(event, "request_context") and event.request_context:
                authorizer = event.request_context.get("authorizer", {})
                return authorizer.get("user_id", "unknown")
        return "unknown"
    except Exception:
        return "unknown"


def extract_user_from_event(event: Any) -> str:
    """Extract user ID from API Gateway event."""
    try:
        if hasattr(event, "request_context") and event.request_context:
            authorizer = event.request_context.get("authorizer", {})
            return authorizer.get("user_id", "unknown")
        return "unknown"
    except Exception:
        return "unknown"
