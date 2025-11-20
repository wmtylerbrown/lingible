from __future__ import annotations

import json

from models.base import HealthResponse
from utils.response import create_model_response


def test_health_response_serialization_matches_api_contract() -> None:
    response = HealthResponse(status="healthy")
    envelope = create_model_response(response)
    body = json.loads(envelope["body"])

    assert body["status"] == "healthy"
