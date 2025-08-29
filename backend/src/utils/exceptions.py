"""Comprehensive exception hierarchy for the application."""

from datetime import datetime
from typing import Optional, Dict, Any
from .logging import logger


class AppException(Exception):
    """Base application exception with structured error information."""

    def __init__(
        self,
        message: str,
        error_code: str,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        log_level: str = "error",
    ) -> None:
        """Initialize application exception."""
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        self.request_id = request_id
        self.timestamp = datetime.utcnow().isoformat()
        self.log_level = log_level

        # Log the exception
        self._log_exception()

    def _log_exception(self) -> None:
        """Log the exception with appropriate level and context."""
        log_data = {
            "error_code": self.error_code,
            "status_code": self.status_code,
            "details": self.details,
            "request_id": self.request_id,
            "timestamp": self.timestamp,
        }

        if self.log_level == "error":
            logger.log_error(self, log_data)
        elif self.log_level == "warning":
            logger.logger.warning(f"Warning: {self.message}", extra=log_data)
        else:
            logger.logger.info(f"Info: {self.message}", extra=log_data)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API response."""
        return {
            "success": False,
            "message": self.message,
            "error_code": self.error_code,
            "status_code": self.status_code,
            "details": self.details,
            "timestamp": self.timestamp,
            "request_id": self.request_id,
        }


# Authentication Exceptions
class AuthenticationError(AppException):
    """Base authentication exception."""

    def __init__(
        self,
        message: str = "Authentication failed",
        error_code: str = "AUTH_001",
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> None:
        super().__init__(message, error_code, 401, details, request_id, "warning")


class InvalidTokenError(AuthenticationError):
    """Invalid or malformed token."""

    def __init__(
        self,
        message: str = "Invalid authentication token",
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> None:
        super().__init__(message, "AUTH_001", details, request_id)


class TokenExpiredError(AuthenticationError):
    """Expired authentication token."""

    def __init__(
        self,
        message: str = "Authentication token has expired",
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> None:
        super().__init__(message, "AUTH_002", details, request_id)


class InsufficientPermissionsError(AuthenticationError):
    """User lacks required permissions."""

    def __init__(
        self,
        message: str = "Insufficient permissions for this operation",
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> None:
        super().__init__(message, "AUTH_003", details, request_id)


# Validation Exceptions
class ValidationError(AppException):
    """Base validation exception."""

    def __init__(
        self,
        message: str = "Validation failed",
        error_code: str = "VAL_001",
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> None:
        super().__init__(message, error_code, 422, details, request_id, "warning")


class MissingRequiredFieldError(ValidationError):
    """Missing required field in request."""

    def __init__(
        self,
        field_name: str,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> None:
        if message is None:
            message = f"Missing required field: {field_name}"
        if details is None:
            details = {"field": field_name}
        super().__init__(message, "VAL_002", details, request_id)


class InvalidFormatError(ValidationError):
    """Invalid data format."""

    def __init__(
        self,
        field_name: str,
        expected_format: str,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> None:
        if message is None:
            message = (
                f"Invalid format for field '{field_name}'. Expected: {expected_format}"
            )
        if details is None:
            details = {"field": field_name, "expected_format": expected_format}
        super().__init__(message, "VAL_003", details, request_id)


# Resource Exceptions
class ResourceError(AppException):
    """Base resource exception."""

    def __init__(
        self,
        message: str = "Resource operation failed",
        error_code: str = "RES_001",
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> None:
        super().__init__(message, error_code, 404, details, request_id, "warning")


class ResourceNotFoundError(ResourceError):
    """Resource not found."""

    def __init__(
        self,
        resource_type: str,
        resource_id: str,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> None:
        if message is None:
            message = f"{resource_type} with id '{resource_id}' not found"
        if details is None:
            details = {"resource_type": resource_type, "resource_id": resource_id}
        super().__init__(message, "RES_001", details, request_id)


class ResourceAlreadyExistsError(ResourceError):
    """Resource already exists."""

    def __init__(
        self,
        resource_type: str,
        resource_id: str,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> None:
        if message is None:
            message = f"{resource_type} with id '{resource_id}' already exists"
        if details is None:
            details = {"resource_type": resource_type, "resource_id": resource_id}
        # Override status code to 409 Conflict
        super().__init__(message, "RES_002", details, request_id)
        self.status_code = 409


class ResourceConflictError(ResourceError):
    """Resource conflict."""

    def __init__(
        self,
        message: str = "Resource conflict occurred",
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> None:
        # Override status code to 409 Conflict
        super().__init__(message, "RES_003", details, request_id)
        self.status_code = 409


# Business Logic Exceptions
class BusinessLogicError(AppException):
    """Base business logic exception."""

    def __init__(
        self,
        message: str = "Business logic error",
        error_code: str = "BIZ_001",
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> None:
        super().__init__(message, error_code, 400, details, request_id, "warning")


class UsageLimitExceededError(BusinessLogicError):
    """User has exceeded their usage limits."""

    def __init__(
        self,
        limit_type: str,
        current_usage: int,
        limit: int,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> None:
        if message is None:
            message = f"Usage limit exceeded for {limit_type}. Current: {current_usage}, Limit: {limit}"
        if details is None:
            details = {
                "limit_type": limit_type,
                "current_usage": current_usage,
                "limit": limit,
            }
        # Override status code to 429 Too Many Requests and use unique error code
        super().__init__(message, "BIZ_001", details, request_id)
        self.status_code = 429
        self.error_code = "USAGE_001"


class InsufficientCreditsError(BusinessLogicError):
    """User has insufficient credits."""

    def __init__(
        self,
        required_credits: int,
        available_credits: int,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> None:
        if message is None:
            message = f"Insufficient credits. Required: {required_credits}, Available: {available_credits}"
        if details is None:
            details = {
                "required_credits": required_credits,
                "available_credits": available_credits,
            }
        # Use unique error code
        super().__init__(message, "BIZ_002", details, request_id)


class ServiceUnavailableError(BusinessLogicError):
    """External service is unavailable."""

    def __init__(
        self,
        service_name: str,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> None:
        if message is None:
            message = f"Service '{service_name}' is currently unavailable"
        if details is None:
            details = {"service_name": service_name}
        # Override status code to 503 Service Unavailable and use unique error code
        super().__init__(message, "BIZ_003", details, request_id)
        self.status_code = 503
        self.error_code = "SERVICE_001"


# System Exceptions
class SystemError(AppException):
    """Base system exception."""

    def __init__(
        self,
        message: str = "System error occurred",
        error_code: str = "SYS_001",
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> None:
        super().__init__(message, error_code, 500, details, request_id, "error")


class DatabaseError(SystemError):
    """Database operation failed."""

    def __init__(
        self,
        operation: str,
        table: str,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> None:
        if message is None:
            message = f"Database operation '{operation}' failed on table '{table}'"
        if details is None:
            details = {"operation": operation, "table": table}
        super().__init__(message, "SYS_001", details, request_id)


class ExternalServiceError(SystemError):
    """External service call failed."""

    def __init__(
        self,
        service_name: str,
        operation: str,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> None:
        if message is None:
            message = (
                f"External service '{service_name}' operation '{operation}' failed"
            )
        if details is None:
            details = {"service_name": service_name, "operation": operation}
        super().__init__(message, "SYS_002", details, request_id)


class InternalError(SystemError):
    """Internal application error."""

    def __init__(
        self,
        message: str = "Internal application error",
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> None:
        super().__init__(message, "SYS_003", details, request_id)


# Rate Limiting Exception
class RateLimitExceededError(AppException):
    """Rate limit exceeded."""

    def __init__(
        self,
        limit: int,
        window_seconds: int,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> None:
        if message is None:
            message = f"Rate limit exceeded. Limit: {limit} requests per {window_seconds} seconds"
        if details is None:
            details = {"limit": limit, "window_seconds": window_seconds}
        super().__init__(message, "RATE_001", 429, details, request_id, "warning")
