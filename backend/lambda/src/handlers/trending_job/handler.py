"""Lambda handler for trending data generation job."""

import json
from aws_lambda_powertools.utilities.typing import LambdaContext

from models.trending import TrendingJobRequest
from services.trending_service import TrendingService
from utils.tracing import tracer
from utils.logging import logger


# Initialize services at module level (Lambda container reuse)
trending_service = TrendingService()


@tracer.trace_lambda
def handler(event: dict, context: LambdaContext) -> dict:
    """Handle trending data generation job requests."""

    try:
        # Parse the job request from the event
        job_request = TrendingJobRequest(**event)

        # Run the trending job
        job_response = trending_service.run_trending_job(job_request)

        # Log successful completion
        logger.log_business_event(
            "trending_job_success",
            {
                "job_id": job_response.job_id,
                "status": job_response.status,
                "terms_processed": job_response.terms_processed,
                "terms_added": job_response.terms_added,
                "terms_updated": job_response.terms_updated,
            },
        )

        # Return the job response
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
            },
            "body": json.dumps(job_response.model_dump()),
        }

    except Exception as e:
        # Log error
        logger.log_error(
            e,
            {
                "operation": "trending_job_handler",
                "event": event,
            },
        )

        # Return error response
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
            },
            "body": json.dumps({
                "error": "Internal server error",
                "message": str(e),
            }),
        }
