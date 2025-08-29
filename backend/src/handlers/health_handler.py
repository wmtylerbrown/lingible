"""Lambda handler for health check endpoint."""

from typing import Dict, Any

from aws_lambda_powertools.utilities.parser import event_parser
from aws_lambda_powertools.utilities.typing import LambdaContext

from ..models.events import HealthEvent
from ..utils.logging import logger
from ..utils.tracing import tracer
from ..utils.decorators import handle_errors
from ..utils.envelopes import HealthEnvelope


# Lambda handler entry point with correct decorator order
@tracer.trace_lambda
@event_parser(model=HealthEvent, envelope=HealthEnvelope())
@handle_errors()
def handler(event: HealthEvent, context: LambdaContext) -> Dict[str, Any]:
    """Handle health check requests."""

    # Log health check request
    logger.log_business_event(
        "health_check_requested",
        {
            "request_id": event.request_id,
            "timestamp": event.timestamp,
        },
    )

    # Return health status data - decorator handles the API response creation
    return {
        "status": "healthy",
        "service": "genz-translation-api",
        "version": "1.0.0",
        "timestamp": event.timestamp,
    }
