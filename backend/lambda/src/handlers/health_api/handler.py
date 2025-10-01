"""Lambda handler for health check endpoint."""

from aws_lambda_powertools.utilities.parser import event_parser
from aws_lambda_powertools.utilities.typing import LambdaContext

from models.events import HealthEvent
from models.base import HealthResponse
from utils.tracing import tracer
from utils.decorators import api_handler
from utils.envelopes import SimpleEnvelope


# Lambda handler entry point with correct decorator order
@tracer.trace_lambda
@event_parser(model=HealthEvent, envelope=SimpleEnvelope)
@api_handler()
def handler(event: HealthEvent, context: LambdaContext) -> HealthResponse:
    """Handle health check requests."""

    # Return health status data using HealthResponse model
    return HealthResponse(
        status="healthy",
    )
