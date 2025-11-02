"""Enhanced response utilities with proper error handling."""

import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from models.base import ErrorResponse, HTTPStatus, ErrorCode
from models.aws import APIGatewayResponse
from .exceptions import AppException


def create_model_response(
    model: Any,
    status_code: int = HTTPStatus.OK.value,
) -> Dict[str, Any]:
    """Create a successful API Gateway response from a Pydantic model."""
    # Use serialize_model() for consistent datetime/Decimal serialization
    json_body = json.dumps(model.serialize_model())

    return APIGatewayResponse(
        statusCode=status_code,
        headers={
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
        },
        body=json_body,
        isBase64Encoded=False,
    ).model_dump()


def create_error_response(
    exception: AppException, request_id: Optional[str] = None
) -> Dict[str, Any]:
    """Create an error API Gateway response from an exception."""
    error_data = ErrorResponse(
        success=False,
        message=exception.message,
        error_code=exception.error_code,
        status_code=exception.status_code,
        details=exception.details,
        timestamp=exception.timestamp,
        request_id=request_id or exception.request_id,
    )

    return APIGatewayResponse(
        statusCode=exception.status_code,
        headers={
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
        },
        body=json.dumps(error_data.serialize_model()),
        isBase64Encoded=False,
    ).model_dump()


def create_validation_error_response(
    message: str,
    details: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a validation error response."""
    error_data = ErrorResponse(
        success=False,
        message=message,
        error_code=ErrorCode.INVALID_INPUT.value,
        status_code=HTTPStatus.UNPROCESSABLE_ENTITY.value,
        details=details,
        timestamp=datetime.now(timezone.utc),
        request_id=request_id,
    )

    return APIGatewayResponse(
        statusCode=HTTPStatus.UNPROCESSABLE_ENTITY.value,
        headers={
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
        },
        body=json.dumps(error_data.serialize_model()),
        isBase64Encoded=False,
    ).model_dump()


def create_unauthorized_response(
    message: str = "Authentication required", request_id: Optional[str] = None
) -> Dict[str, Any]:
    """Create an unauthorized error response."""
    error_data = ErrorResponse(
        success=False,
        message=message,
        error_code=ErrorCode.INVALID_TOKEN.value,
        status_code=HTTPStatus.UNAUTHORIZED.value,
        details={"reason": "authentication_required"},
        timestamp=datetime.now(timezone.utc),
        request_id=request_id,
    )

    return APIGatewayResponse(
        statusCode=HTTPStatus.UNAUTHORIZED.value,
        headers={
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
        },
        body=json.dumps(error_data.serialize_model()),
        isBase64Encoded=False,
    ).model_dump()


def create_rate_limit_response(
    limit: int, window_seconds: int, request_id: Optional[str] = None
) -> Dict[str, Any]:
    """Create a rate limit exceeded response."""
    error_data = ErrorResponse(
        success=False,
        message=f"Rate limit exceeded. Limit: {limit} requests per {window_seconds} seconds",
        error_code=ErrorCode.RATE_LIMIT_EXCEEDED.value,
        status_code=HTTPStatus.TOO_MANY_REQUESTS.value,
        details={"limit": limit, "window_seconds": window_seconds},
        timestamp=datetime.now(timezone.utc),
        request_id=request_id,
    )

    return APIGatewayResponse(
        statusCode=HTTPStatus.TOO_MANY_REQUESTS.value,
        headers={
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
        },
        body=json.dumps(error_data.serialize_model()),
        isBase64Encoded=False,
    ).model_dump()
