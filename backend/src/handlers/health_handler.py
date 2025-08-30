"""Lambda handler for health check endpoint."""

from typing import Dict, Any

from aws_lambda_powertools.utilities.parser import event_parser
from aws_lambda_powertools.utilities.typing import LambdaContext

from ..models.events import HealthEvent
from ..utils.tracing import tracer
from ..utils.decorators import api_handler
from ..utils.envelopes import HealthEnvelope


# Lambda handler entry point with correct decorator order
@tracer.trace_lambda
@event_parser(model=HealthEvent, envelope=HealthEnvelope())
@api_handler()
def handler(event: HealthEvent, context: LambdaContext) -> Dict[str, Any]:
    """Handle health check requests."""

    # Log health check request
    # Return health status data - decorator handles the API response creation
    return {
        "status": "healthy",
        "service": "genz-translation-api",
        "version": "1.0.0",
        "timestamp": event.timestamp,
    }
