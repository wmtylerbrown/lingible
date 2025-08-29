"""Dynamic configuration management using Lambda Powertools and SSM Parameter Store."""

import os
import json
from typing import Dict, Any
from aws_lambda_powertools.utilities.parameters import get_parameter


class AppConfig:
    """Application configuration manager with SSM Parameter Store integration."""

    def __init__(self) -> None:
        """Initialize configuration manager."""
        self.environment = os.environ.get("ENVIRONMENT", "development")
        self.app_name = os.environ.get("APP_NAME", "mobile-app-backend")

        # Default values for development/local testing
        self._defaults = self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration values."""
        return {
            # Environment
            "environment": self.environment,
            "app_name": self.app_name,
            # Logging
            "logging": {
                "level": "INFO" if self.environment == "production" else "DEBUG",
                "enable_correlation": True,
                "enable_structured_logging": True,
            },
            # Tracing
            "tracing": {
                "enabled": True,
                "service_name": self.app_name,
                "auto_patch": False,
                "capture_response": True,
                "capture_error": True,
            },
            # Usage Limits
            "usage_limits": {
                "free": {"daily_limit": 5, "max_text_length": 500},
                "premium": {
                    "daily_limit": 20,
                    "max_text_length": 1000,
                },
            },
            # Bedrock Configuration
            "bedrock": {
                "model": "anthropic.claude-3-sonnet-20240229-v1:0",
                "region": "us-east-1",
                "max_tokens": 1000,
                "temperature": 0.7,
            },
            # Translation Configuration
            "translation": {
                "directions": {
                    "genz_to_english": "genz_to_english",
                    "english_to_genz": "english_to_genz",
                },
                "max_concurrent_translations": 5,
                "translation_timeout": 30,
            },
            # Database Configuration
            "database": {
                "tables": {
                    "users": f"{self.app_name}-users-{self.environment}",
                    "translations": f"{self.app_name}-translations-{self.environment}",
                    "translation_history": f"{self.app_name}-translation-history-{self.environment}",
                    "usage_tracking": f"{self.app_name}-usage-tracking-{self.environment}",
                },
                "read_capacity": 5,
                "write_capacity": 5,
            },
            # Security Configuration
            "security": {
                "sensitive_fields": [
                    "password",
                    "token",
                    "secret",
                    "key",
                    "authorization",
                    "cookie",
                    "x-api-key",
                ],
                "bearer_prefix": "Bearer ",
                "jwt_expiration": 3600,
                "rate_limiting": {
                    "enabled": True,
                    "requests_per_minute": 100,
                    "burst_limit": 20,
                },
            },
            # API Configuration
            "api": {
                "cors": {
                    "allowed_origins": ["*"],
                    "allowed_headers": ["Content-Type", "Authorization"],
                    "allowed_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                },
                "pagination": {"default_limit": 20, "max_limit": 100},
            },
            # Monitoring Configuration
            "monitoring": {
                "enable_metrics": True,
                "enable_logging": True,
                "enable_tracing": True,
                "log_retention_days": 14,
                "metrics_namespace": f"{self.app_name}/{self.environment}",
            },
        }

    def _get_ssm_parameter(self, parameter_name: str, default: Any = None) -> Any:
        """Get parameter from SSM Parameter Store using Powertools caching."""
        try:
            # Get from SSM Parameter Store using Powertools built-in caching (5 minutes)
            full_parameter_name = (
                f"/{self.app_name}/{self.environment}/{parameter_name}"
            )
            value = get_parameter(full_parameter_name, max_age=300)

            # Parse JSON if it's a string
            if isinstance(value, str):
                try:
                    value = json.loads(value)
                except json.JSONDecodeError:
                    pass  # Keep as string if not JSON

            return value

        except Exception:
            # Return default if SSM fails
            return default

    def _get_ssm_parameters(self, parameter_names: list[str]) -> Dict[str, Any]:
        """Get multiple parameters from SSM Parameter Store."""
        try:
            # Get parameters one by one since get_parameters expects a path pattern
            result = {}
            for name in parameter_names:
                value = self._get_ssm_parameter(name)
                if value is not None:
                    result[name] = value
            return result

        except Exception:
            return {}

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value with SSM fallback."""
        # Try to get from SSM first
        ssm_value = self._get_ssm_parameter(key, default)
        if ssm_value is not None:
            return ssm_value

        # Fall back to defaults
        keys = key.split(".")
        value = self._defaults

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def get_usage_limits(self) -> Dict[str, Dict[str, int]]:
        """Get usage limits configuration."""
        return self.get("usage_limits", self._defaults["usage_limits"])

    def get_bedrock_config(self) -> Dict[str, Any]:
        """Get Bedrock configuration."""
        return self.get("bedrock", self._defaults["bedrock"])

    def get_translation_config(self) -> Dict[str, Any]:
        """Get translation configuration."""
        return self.get("translation", self._defaults["translation"])

    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration."""
        return self.get("database", self._defaults["database"])

    def get_security_config(self) -> Dict[str, Any]:
        """Get security configuration."""
        return self.get("security", self._defaults["security"])

    def get_api_config(self) -> Dict[str, Any]:
        """Get API configuration."""
        return self.get("api", self._defaults["api"])

    def get_monitoring_config(self) -> Dict[str, Any]:
        """Get monitoring configuration."""
        return self.get("monitoring", self._defaults["monitoring"])

    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration."""
        return self.get("logging", self._defaults["logging"])

    def get_tracing_config(self) -> Dict[str, Any]:
        """Get tracing configuration."""
        return self.get("tracing", self._defaults["tracing"])

    def refresh_cache(self) -> None:
        """Refresh the configuration cache."""
        # Powertools handles caching automatically - this is a no-op for compatibility
        pass

    def get_all_config(self) -> Dict[str, Any]:
        """Get all configuration values."""
        return {
            "environment": self.environment,
            "app_name": self.app_name,
            "usage_limits": self.get_usage_limits(),
            "bedrock": self.get_bedrock_config(),
            "translation": self.get_translation_config(),
            "database": self.get_database_config(),
            "security": self.get_security_config(),
            "api": self.get_api_config(),
            "monitoring": self.get_monitoring_config(),
            "logging": self.get_logging_config(),
            "tracing": self.get_tracing_config(),
        }


# Global configuration instance
config = AppConfig()


def get_config() -> AppConfig:
    """Get the global configuration instance."""
    return config
