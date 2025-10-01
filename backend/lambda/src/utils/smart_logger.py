"""Smart logging configuration with cost optimization and enhanced debugging."""

import json
from typing import Dict, Any, Optional
from aws_lambda_powertools import Logger
from aws_lambda_powertools.logging import correlation_paths
from .config import get_config_service, ObservabilityConfig, SecurityConfig

# Get configuration
config_service = get_config_service()


class SmartLogger:
    """Smart logger with cost optimization, sensitive data protection, and enhanced debugging."""

    def __init__(self) -> None:
        """Initialize smart logger."""
        observability_config = config_service.get_config(ObservabilityConfig)
        self.environment = config_service.environment
        self.is_debug = observability_config.log_level == "DEBUG"

        # Use POWERTOOLS_SERVICE_NAME environment variable (set per Lambda function)
        self.logger = Logger(
            level=observability_config.log_level,
            correlation_paths=[
                correlation_paths.API_GATEWAY_REST,
                correlation_paths.API_GATEWAY_HTTP,
            ],
        )

    def log_request(self, event: Dict[str, Any], include_body: bool = False) -> None:
        """Log API request with selective body inclusion."""
        log_data = {
            "http_method": event.get("httpMethod"),
            "path": event.get("path"),
            "query_params": event.get("queryStringParameters"),
            "headers": self._sanitize_headers(event.get("headers", {})),
        }

        if include_body and self.environment != "production":
            body = event.get("body")
            if body is not None:
                log_data["body"] = self._sanitize_body(str(body))

        self.logger.info("API Request", extra=log_data)

    def log_response(self, response: Dict[str, Any], duration_ms: float) -> None:
        """Log API response with performance metrics."""
        log_data = {
            "status_code": response.get("statusCode"),
            "duration_ms": duration_ms,
            "response_size": len(response.get("body", "")),
        }

        # Only log response body for errors or in development
        if response.get("statusCode", 200) >= 400 or self.environment == "dev":
            log_data["response_body"] = response.get("body")

        self.logger.info("API Response", extra=log_data)

    def log_error(
        self, error: Exception, context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log errors with context and safe serialization."""
        # Safely serialize context to avoid JSON serialization errors
        safe_context = self._safe_serialize(context or {})

        log_data = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": safe_context,
        }

        # Add debug information in development
        if self.is_debug:
            log_data["debug_info"] = {
                "error_module": getattr(error, "__module__", "unknown"),
                "error_file": (
                    getattr(error, "__traceback__", {})
                    .get("tb_frame", {})
                    .get("f_code", {})
                    .get("co_filename", "unknown")
                    if hasattr(error, "__traceback__")
                    else "unknown"
                ),
                "error_line": (
                    getattr(error, "__traceback__", {}).get("tb_lineno", "unknown")
                    if hasattr(error, "__traceback__")
                    else "unknown"
                ),
            }

        self.logger.error("Error occurred", extra=log_data)

    def log_business_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Log business events (user actions, etc.)."""
        # Safely serialize data to avoid JSON serialization errors
        safe_data = self._safe_serialize(data)
        if isinstance(safe_data, dict):
            self.logger.info(f"Business Event: {event_type}", extra=safe_data)
        else:
            self.logger.info(f"Business Event: {event_type}", extra={"data": safe_data})

    def log_debug(self, message: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Log debug information (only in development)."""
        if self.is_debug:
            log_data = {"debug_message": message}
            if data:
                safe_data = self._safe_serialize(data)
                if isinstance(safe_data, dict):
                    log_data.update(safe_data)
                else:
                    log_data["debug_data"] = safe_data
            self.logger.debug("Debug Info", extra=log_data)

    def log_api_call(self, operation: str, details: Dict[str, Any]) -> None:
        """Log API calls with detailed information."""
        log_data = {
            "operation": operation,
            "details": self._safe_serialize(details),
        }

        if self.is_debug:
            log_data["debug_timestamp"] = self._get_timestamp()

        self.logger.info(f"API Call: {operation}", extra=log_data)

    def log_performance(
        self,
        operation: str,
        duration_ms: float,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log performance metrics."""
        log_data = {
            "operation": operation,
            "duration_ms": duration_ms,
            "performance_category": (
                "fast"
                if duration_ms < 100
                else "slow" if duration_ms < 1000 else "very_slow"
            ),
        }

        if details:
            log_data["details"] = self._safe_serialize(details)

        self.logger.info(f"Performance: {operation}", extra=log_data)

    def _sanitize_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Remove sensitive data from headers."""
        security_config = config_service.get_config(SecurityConfig)
        sensitive_fields = security_config.sensitive_field_patterns
        sanitized = headers.copy()
        for field in sensitive_fields:
            if field.lower() in sanitized:
                sanitized[field.lower()] = "[REDACTED]"
        return sanitized

    def _sanitize_body(self, body: str) -> str:
        """Remove sensitive data from request/response body."""
        if not body:
            return body

        security_config = config_service.get_config(SecurityConfig)
        sensitive_fields = security_config.sensitive_field_patterns

        # Simple redaction - in production, use more sophisticated parsing
        sanitized = body
        for field in sensitive_fields:
            if field.lower() in sanitized.lower():
                sanitized = sanitized.replace(field, "[REDACTED]")
        return sanitized

    def _safe_serialize(self, data: Any) -> Any:
        """Safely serialize data for logging, handling non-serializable objects."""
        if data is None:
            return None

        if isinstance(data, (str, int, float, bool)):
            return data

        if isinstance(data, dict):
            result = {}
            for key, value in data.items():
                try:
                    # Try to serialize the value
                    json.dumps(value)
                    result[key] = self._safe_serialize(value)
                except (TypeError, ValueError):
                    # If it's not serializable, convert to string representation
                    if hasattr(value, "__dict__"):
                        # For objects with __dict__, try to serialize their attributes
                        try:
                            result[key] = self._safe_serialize(value.__dict__)
                        except Exception:
                            result[key] = f"<{type(value).__name__} object>"
                    else:
                        result[key] = f"<{type(value).__name__}: {str(value)[:100]}>"
            return result

        if isinstance(data, (list, tuple)):
            return [self._safe_serialize(item) for item in data]

        # For Pydantic models, try to get their dict representation
        if hasattr(data, "model_dump"):
            try:
                return self._safe_serialize(data.model_dump())
            except Exception:
                pass

        # For any other object, return a string representation
        return f"<{type(data).__name__}: {str(data)[:100]}>"

    def _get_timestamp(self) -> str:
        """Get current timestamp for debug logging."""
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).isoformat()


# Global logger instance
logger = SmartLogger()
