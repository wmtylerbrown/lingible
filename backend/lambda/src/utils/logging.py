"""Smart logging configuration with cost optimization."""

from typing import Dict, Any, Optional
from aws_lambda_powertools import Logger
from aws_lambda_powertools.logging import correlation_paths
from .config import get_config

# Get configuration
config = get_config()


class SmartLogger:
    """Smart logger with cost optimization and sensitive data protection."""

    def __init__(self, service_name: str) -> None:
        """Initialize smart logger."""
        logging_config = config.get_logging_config()

        self.logger = Logger(
            service=service_name,
            level=logging_config["level"],
            correlation_paths=[
                correlation_paths.API_GATEWAY_REST,
                correlation_paths.API_GATEWAY_HTTP,
            ],
        )

    def log_request(self, event: Dict[str, Any], include_body: bool = False) -> None:
        """Log API request with selective body inclusion."""
        environment = config.get("environment", "development")

        log_data = {
            "http_method": event.get("httpMethod"),
            "path": event.get("path"),
            "query_params": event.get("queryStringParameters"),
            "headers": self._sanitize_headers(event.get("headers", {})),
        }

        if include_body and environment != "production":
            body = event.get("body")
            if body is not None:
                log_data["body"] = self._sanitize_body(str(body))

        self.logger.info("API Request", extra=log_data)

    def log_response(self, response: Dict[str, Any], duration_ms: float) -> None:
        """Log API response with performance metrics."""
        environment = config.get("environment", "development")

        log_data = {
            "status_code": response.get("statusCode"),
            "duration_ms": duration_ms,
            "response_size": len(response.get("body", "")),
        }

        # Only log response body for errors or in development
        if response.get("statusCode", 200) >= 400 or environment == "development":
            log_data["response_body"] = response.get("body")

        self.logger.info("API Response", extra=log_data)

    def log_error(
        self, error: Exception, context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log errors with context."""
        log_data = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context or {},
        }

        self.logger.error("Error occurred", extra=log_data)

    def log_business_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Log business events (user actions, etc.)."""
        environment = config.get("environment", "development")

        # Only log business events in staging/production, not development
        if environment != "development":
            self.logger.info(f"Business Event: {event_type}", extra=data)

    def _sanitize_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Remove sensitive data from headers."""
        sensitive_fields = config.get_security_config()["sensitive_fields"]
        sanitized = headers.copy()
        for field in sensitive_fields:
            if field.lower() in sanitized:
                sanitized[field.lower()] = "[REDACTED]"
        return sanitized

    def _sanitize_body(self, body: str) -> str:
        """Remove sensitive data from request/response body."""
        if not body:
            return body

        sensitive_fields = config.get_security_config()["sensitive_fields"]

        # Simple redaction - in production, use more sophisticated parsing
        sanitized = body
        for field in sensitive_fields:
            if field.lower() in sanitized.lower():
                sanitized = sanitized.replace(field, "[REDACTED]")
        return sanitized


# Global logger instance
logger = SmartLogger("lingible-backend")
