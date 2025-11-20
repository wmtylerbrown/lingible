"""Base API response models."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence

from pydantic import BaseModel, Field, model_validator


class HTTPStatus(Enum):
    """HTTP status codes for API responses."""

    # Success codes
    OK = 200
    CREATED = 201
    NO_CONTENT = 204

    # Client error codes
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    CONFLICT = 409
    UNPROCESSABLE_ENTITY = 422
    TOO_MANY_REQUESTS = 429

    # Server error codes
    INTERNAL_SERVER_ERROR = 500
    SERVICE_UNAVAILABLE = 503


class ErrorCode(Enum):
    """Application-specific error codes."""

    # Authentication errors
    INVALID_TOKEN = "AUTH_001"
    TOKEN_EXPIRED = "AUTH_002"
    INSUFFICIENT_PERMISSIONS = "AUTH_003"
    AUTHENTICATION_ERROR = "AUTH_001"
    AUTHORIZATION_ERROR = "AUTH_003"

    # Validation errors
    INVALID_INPUT = "VAL_001"
    MISSING_REQUIRED_FIELD = "VAL_002"
    INVALID_FORMAT = "VAL_003"
    VALIDATION_ERROR = "VAL_001"

    # Resource errors
    RESOURCE_NOT_FOUND = "RES_001"
    RESOURCE_ALREADY_EXISTS = "RES_002"
    RESOURCE_CONFLICT = "RES_003"

    # Business logic (legacy aliases)
    BUSINESS_LOGIC_ERROR = "BIZ_003"
    SUBSCRIPTION_REQUIRED = "BIZ_004"

    # Business logic errors
    USAGE_LIMIT_EXCEEDED = "BIZ_001"
    INSUFFICIENT_CREDITS = "BIZ_002"
    SERVICE_UNAVAILABLE = "BIZ_003"

    # System errors
    DATABASE_ERROR = "SYS_001"
    EXTERNAL_SERVICE_ERROR = "SYS_002"
    INTERNAL_ERROR = "SYS_003"
    SYSTEM_ERROR = "SYS_003"

    # Rate limiting errors
    RATE_LIMIT_EXCEEDED = "RATE_001"


class LingibleBaseModel(BaseModel):
    """Base model for all Lingible models with automatic serialization handling."""

    @model_validator(mode="before")
    @classmethod
    def _normalize_input(cls, data: Any) -> Any:
        """Normalize inbound data prior to model construction."""
        if isinstance(data, Mapping):
            return {key: cls.__normalize_value(value) for key, value in data.items()}
        if isinstance(data, Sequence) and not isinstance(data, (str, bytes, bytearray)):
            return [cls.__normalize_value(item) for item in data]
        return cls.__normalize_value(data)

    @classmethod
    def __normalize_value(cls, value: Any) -> Any:
        """Recursively normalize raw DynamoDB-style values."""
        if isinstance(value, LingibleBaseModel):
            return value
        if isinstance(value, Mapping):
            normalized: MutableMapping[Any, Any] = {}
            for key, inner in value.items():
                normalized[key] = cls.__normalize_value(inner)
            return dict(normalized)
        if isinstance(value, Sequence) and not isinstance(
            value, (str, bytes, bytearray)
        ):
            return [cls.__normalize_value(item) for item in value]
        if isinstance(value, set):
            return [cls.__normalize_value(item) for item in value]
        if isinstance(value, Decimal):
            # Preserve integers when possible, otherwise cast to float.
            if value == value.to_integral_value():
                return int(value)
            return float(value)
        if isinstance(value, str):
            lowered = value.lower()
            if lowered in {"true", "false"}:
                return lowered == "true"
        return value

    class Config:
        """Pydantic configuration for consistent serialization."""

        # Preserve enum types internally for stronger typing
        use_enum_values = False
        # Validate assignment to catch type errors early
        validate_assignment = True
        # Allow population by field name or alias
        populate_by_name = True
        # Allow creation from ORM objects (future-proofing)
        from_attributes = True
        # Use custom serializers for complex types
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: float(v),
        }

    def serialize_model(self) -> Dict[str, Any]:
        """Convert the model into a JSON-serializable dictionary."""
        raw_data = self.model_dump(mode="python", by_alias=True)
        return {key: self._serialize_value(value) for key, value in raw_data.items()}

    @classmethod
    def _serialize_value(cls, value: Any) -> Any:
        """Recursively normalize nested values for JSON serialization."""
        if isinstance(value, LingibleBaseModel):
            return value.serialize_model()
        if isinstance(value, Mapping):
            return {key: cls._serialize_value(inner) for key, inner in value.items()}
        if isinstance(value, Sequence) and not isinstance(
            value, (str, bytes, bytearray)
        ):
            return [cls._serialize_value(item) for item in value]
        if isinstance(value, set):
            return [cls._serialize_value(item) for item in value]
        if isinstance(value, Decimal):
            return int(value) if value == value.to_integral_value() else float(value)
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, Enum):
            return value.value
        return value

    def to_json(self) -> str:
        """Convert model to JSON string with proper serialization."""
        # Use Pydantic's built-in JSON encoding which properly handles enums and aliases
        return self.model_dump_json(by_alias=True)

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary with proper serialization."""
        return self.serialize_model()

    def to_dynamodb(self) -> Dict[str, Any]:
        """Convert model to DynamoDB-compatible dictionary.

        Converts float values to Decimal (DynamoDB requirement) while preserving
        other types. This is the inverse of _normalize_input which converts
        Decimal to float when reading from DynamoDB.

        Returns:
            Dictionary suitable for DynamoDB put_item/update_item operations
        """
        raw_data = self.model_dump(mode="python", by_alias=True)
        return {key: self._to_dynamodb_value(value) for key, value in raw_data.items()}

    @classmethod
    def _to_dynamodb_value(cls, value: Any) -> Any:
        """Recursively convert values to DynamoDB-compatible types."""
        if isinstance(value, LingibleBaseModel):
            return value.to_dynamodb()
        if isinstance(value, Mapping):
            return {key: cls._to_dynamodb_value(inner) for key, inner in value.items()}
        if isinstance(value, Sequence) and not isinstance(
            value, (str, bytes, bytearray)
        ):
            return [cls._to_dynamodb_value(item) for item in value]
        if isinstance(value, set):
            return [cls._to_dynamodb_value(item) for item in value]
        if isinstance(value, float):
            # Convert float to Decimal for DynamoDB (DynamoDB doesn't support float)
            return Decimal(str(value))
        if isinstance(value, Decimal):
            # Already Decimal, keep as-is
            return value
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, Enum):
            return value.value
        return value


class BaseResponse(LingibleBaseModel):
    """Base API response model."""

    success: bool = Field(..., description="Whether the request was successful")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")
    timestamp: datetime = Field(..., description="Response timestamp")


class ErrorResponse(LingibleBaseModel):
    """Standardized error response model."""

    success: bool = Field(False, description="Always false for error responses")
    message: str = Field(..., description="Human-readable error message")
    error_code: str = Field(..., description="Application-specific error code")
    status_code: int = Field(..., description="HTTP status code")
    details: Optional[Dict[str, Any]] = Field(
        None, description="Additional error details"
    )
    timestamp: datetime = Field(..., description="Error timestamp")
    request_id: Optional[str] = Field(None, description="Request ID for tracing")


class PaginationParams(BaseModel):
    """Pagination parameters for list requests."""

    limit: int = Field(default=20, ge=1, le=100, description="Number of items per page")
    offset: int = Field(default=0, ge=0, description="Number of items to skip")
    sort_by: Optional[str] = Field(None, description="Field to sort by")
    sort_order: str = Field(
        default="desc", pattern="^(asc|desc)$", description="Sort order"
    )


class PaginatedResponse(LingibleBaseModel):
    """Paginated response model."""

    success: bool = Field(True, description="Whether the request was successful")
    data: List[Dict[str, Any]] = Field(..., description="List of items")
    pagination: Dict[str, Any] = Field(..., description="Pagination information")
    timestamp: datetime = Field(..., description="Response timestamp")


class HealthResponse(LingibleBaseModel):
    """Health check response model."""

    status: str = Field(..., description="Service status (healthy, unhealthy, etc.)")
