"""Decorators for Lambda handlers."""

import functools
from typing import Any, Callable, Dict, Optional
from pydantic import BaseModel

from .response import (
    create_model_response,
    create_validation_error_response,
    create_unauthorized_response,
    create_rate_limit_response,
    create_error_response,
)
from .exceptions import (
    ValidationError,
    AuthenticationError,
    InsufficientPermissionsError,
    RateLimitExceededError,
    AppException,
)
from .smart_logger import logger


def api_handler(
    extract_user_id: Optional[Callable] = None,
    user_id: Optional[str] = None,
) -> Callable:
    """
    Decorator for API Gateway Lambda handlers.

    Args:
        extract_user_id: Function to extract user ID from parsed data
        user_id: Direct user ID if available

    Returns:
        Decorated function that handles common API Gateway patterns
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Dict[str, Any]:
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

                # If the result is a Pydantic model, create a success response
                if isinstance(result, BaseModel):
                    return create_model_response(result)

                # For any other result type, return as-is (backward compatibility)
                return result

            except ValidationError as e:
                logger.log_error(
                    e, {"user_id": current_user_id, "error_type": "validation"}
                )
                return create_validation_error_response(str(e))

            except InsufficientPermissionsError as e:
                # Handle InsufficientPermissionsError BEFORE AuthenticationError
                # because it extends AuthenticationError but needs 403 status code
                logger.log_error(
                    e,
                    {
                        "user_id": current_user_id,
                        "error_type": "insufficient_permissions",
                    },
                )
                return create_error_response(e)

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

            except AppException as e:
                # Handle all AppException subclasses using their own status codes and error codes
                logger.log_error(
                    e,
                    {
                        "user_id": current_user_id,
                        "error_type": e.__class__.__name__.lower(),
                    },
                )
                return create_error_response(e)

            except Exception as e:
                logger.log_error(
                    e, {"user_id": current_user_id, "error_type": "unknown"}
                )
                return (
                    create_error_response(e)
                    if isinstance(e, AppException)
                    else create_error_response(
                        AppException("An unexpected error occurred", "SYS_003", 500)
                    )
                )

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
