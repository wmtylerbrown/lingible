"""Enhanced response utilities with proper error handling."""

import json
from datetime import datetime
from typing import Optional, Dict, Any
from ..models.base import ErrorResponse, HTTPStatus, ErrorCode
from ..models.aws import APIGatewayResponse
from .exceptions import AppException


def create_success_response(
    data: Optional[Dict[str, Any]] = None,
    status_code: int = HTTPStatus.OK.value,
) -> APIGatewayResponse:
    """Create a successful API Gateway response."""
    return APIGatewayResponse(
        statusCode=status_code,
        headers={
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
        },
        body=json.dumps(data) if data else "{}",
        isBase64Encoded=False,
    )


def create_model_response(
    model: Any,
    status_code: int = HTTPStatus.OK.value,
) -> APIGatewayResponse:
    """Create a successful API Gateway response from a Pydantic model."""
    return APIGatewayResponse(
        statusCode=status_code,
        headers={
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
        },
        body=model.model_dump_json(),
        isBase64Encoded=False,
    )


def create_error_response(
    exception: AppException, request_id: Optional[str] = None
) -> APIGatewayResponse:
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
        body=error_data.model_dump_json(),
        isBase64Encoded=False,
    )


def create_validation_error_response(
    message: str,
    details: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None,
) -> APIGatewayResponse:
    """Create a validation error response."""
    error_data = ErrorResponse(
        success=False,
        message=message,
        error_code=ErrorCode.INVALID_INPUT.value,
        status_code=HTTPStatus.UNPROCESSABLE_ENTITY.value,
        details=details,
        timestamp=datetime.utcnow().isoformat(),
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
        body=error_data.model_dump_json(),
        isBase64Encoded=False,
    )


def create_not_found_response(
    resource_type: str, resource_id: str, request_id: Optional[str] = None
) -> APIGatewayResponse:
    """Create a not found error response."""
    error_data = ErrorResponse(
        success=False,
        message=f"{resource_type} with id '{resource_id}' not found",
        error_code=ErrorCode.RESOURCE_NOT_FOUND.value,
        status_code=HTTPStatus.NOT_FOUND.value,
        details={"resource_type": resource_type, "resource_id": resource_id},
        timestamp=datetime.utcnow().isoformat(),
        request_id=request_id,
    )

    return APIGatewayResponse(
        statusCode=HTTPStatus.NOT_FOUND.value,
        headers={
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
        },
        body=error_data.model_dump_json(),
        isBase64Encoded=False,
    )


def create_unauthorized_response(
    message: str = "Authentication required", request_id: Optional[str] = None
) -> APIGatewayResponse:
    """Create an unauthorized error response."""
    error_data = ErrorResponse(
        success=False,
        message=message,
        error_code=ErrorCode.INVALID_TOKEN.value,
        status_code=HTTPStatus.UNAUTHORIZED.value,
        details={"reason": "authentication_required"},
        timestamp=datetime.utcnow().isoformat(),
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
        body=error_data.model_dump_json(),
        isBase64Encoded=False,
    )


def create_forbidden_response(
    message: str = "Insufficient permissions", request_id: Optional[str] = None
) -> APIGatewayResponse:
    """Create a forbidden error response."""
    error_data = ErrorResponse(
        success=False,
        message=message,
        error_code=ErrorCode.INSUFFICIENT_PERMISSIONS.value,
        status_code=HTTPStatus.FORBIDDEN.value,
        details={"reason": "insufficient_permissions"},
        timestamp=datetime.utcnow().isoformat(),
        request_id=request_id,
    )

    return APIGatewayResponse(
        statusCode=HTTPStatus.FORBIDDEN.value,
        headers={
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
        },
        body=error_data.model_dump_json(),
        isBase64Encoded=False,
    )


def create_rate_limit_response(
    limit: int, window_seconds: int, request_id: Optional[str] = None
) -> APIGatewayResponse:
    """Create a rate limit exceeded response."""
    error_data = ErrorResponse(
        success=False,
        message=f"Rate limit exceeded. Limit: {limit} requests per {window_seconds} seconds",
        error_code=ErrorCode.RATE_LIMIT_EXCEEDED.value,
        status_code=HTTPStatus.TOO_MANY_REQUESTS.value,
        details={"limit": limit, "window_seconds": window_seconds},
        timestamp=datetime.utcnow().isoformat(),
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
        body=error_data.model_dump_json(),
        isBase64Encoded=False,
    )


def create_internal_error_response(
    message: str = "Internal server error", request_id: Optional[str] = None
) -> APIGatewayResponse:
    """Create an internal server error response."""
    error_data = ErrorResponse(
        success=False,
        message=message,
        error_code=ErrorCode.INTERNAL_ERROR.value,
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR.value,
        details={"reason": "internal_error"},
        timestamp=datetime.utcnow().isoformat(),
        request_id=request_id,
    )

    return APIGatewayResponse(
        statusCode=HTTPStatus.INTERNAL_SERVER_ERROR.value,
        headers={
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
        },
        body=error_data.model_dump_json(),
        isBase64Encoded=False,
    )


def response_to_dict(response: APIGatewayResponse) -> Dict[str, Any]:
    """Convert APIGatewayResponse to dictionary for Lambda compatibility."""
    return {
        "statusCode": response.statusCode,
        "headers": response.headers,
        "body": response.body,
    }
