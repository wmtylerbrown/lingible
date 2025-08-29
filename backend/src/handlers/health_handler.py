"""Lambda handler for health check endpoint."""

from typing import Dict, Any

from aws_lambda_powertools.utilities.parser import event_parser
from aws_lambda_powertools.utilities.typing import LambdaContext

from ..models.aws import APIGatewayResponse
from ..utils.logging import logger
from ..utils.tracing import tracer
from ..utils.response import create_success_response
from ..utils.decorators import handle_errors
from ..utils.envelopes import HealthEnvelope


# Lambda handler entry point with correct decorator order
@tracer.trace_lambda
@event_parser(model=Dict[str, Any], envelope=HealthEnvelope())
@handle_errors(success_message="Service is healthy")
def handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """Handle health check requests."""

    # Log health check request
    logger.log_business_event(
        "health_check_requested",
        {
            "request_id": event.get("request_id"),
            "timestamp": event.get("timestamp"),
        },
    )

    # Return health status data - decorator handles the API response creation
    return {
        "status": "healthy",
        "service": "genz-translation-api",
        "version": "1.0.0",
        "timestamp": event.get("timestamp"),
    }
