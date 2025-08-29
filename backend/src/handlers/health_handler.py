"""Lambda handler for health check endpoint."""

from typing import Dict, Any

from aws_lambda_powertools.utilities.parser import event_parser
from aws_lambda_powertools.utilities.typing import LambdaContext

from ..models.aws import APIGatewayResponse
from ..utils.logging import logger
from ..utils.tracing import tracer
from ..utils.response import create_success_response
from ..utils.decorators import handle_errors
from ..utils.envelopes import APIGatewayEnvelope


class HealthEnvelope(APIGatewayEnvelope):
    """Envelope for health check endpoints."""

    def _parse_api_gateway(
        self, event: Any, model: type, base_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse health check specific data."""
        # For GET requests, we don't need to parse a request body
        # Just return the base data
        return base_data


# Lambda handler entry point with correct decorator order
@tracer.trace_lambda
@event_parser(model=Dict[str, Any], envelope=HealthEnvelope())
@handle_errors()
def handler(event: Dict[str, Any], context: LambdaContext) -> APIGatewayResponse:
    """Handle health check requests."""

    # Log health check request
    logger.log_business_event(
        "health_check_requested",
        {
            "request_id": event.get("request_id"),
            "timestamp": event.get("timestamp"),
        },
    )

    # Return success response with health status
    return create_success_response(
        "Service is healthy",
        {
            "status": "healthy",
            "service": "genz-translation-api",
            "version": "1.0.0",
            "timestamp": event.get("timestamp"),
        },
    )
