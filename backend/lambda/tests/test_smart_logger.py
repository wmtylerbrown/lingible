"""Tests for SmartLogger."""

import pytest
import json
from unittest.mock import patch

from utils.smart_logger import SmartLogger


class TestSmartLogger:
    """Test SmartLogger."""

    def test_logger_initialization(self):
        """Test SmartLogger initialization."""
        logger = SmartLogger()

        assert logger.environment is not None
        assert logger.logger is not None

    @patch('utils.smart_logger.Logger')
    @patch('utils.smart_logger.get_config_service')
    def test_log_business_event(self, mock_config_service, mock_logger_class):
        """Test logging business events."""
        logger = SmartLogger()

        logger.log_business_event("user_created", {"user_id": "test_123"})

        mock_logger_class.return_value.info.assert_called_once()

    @patch('utils.smart_logger.Logger')
    @patch('utils.smart_logger.get_config_service')
    def test_log_error(self, mock_config_service, mock_logger_class):
        """Test logging errors."""
        logger = SmartLogger()
        error = Exception("Test error")

        logger.log_error(error, {"operation": "test"})

        mock_logger_class.return_value.error.assert_called_once()

    @patch('utils.smart_logger.Logger')
    @patch('utils.smart_logger.get_config_service')
    def test_log_request(self, mock_config_service, mock_logger_class):
        """Test logging requests."""
        logger = SmartLogger()

        logger.log_request(
            {
                "httpMethod": "POST",
                "path": "/translate",
                "headers": {},
                "queryStringParameters": {"user_id": "test_123"},
            }
        )

        mock_logger_class.return_value.info.assert_called_once()

    @patch('utils.smart_logger.Logger')
    @patch('utils.smart_logger.get_config_service')
    def test_log_response(self, mock_config_service, mock_logger_class):
        """Test logging responses."""
        logger = SmartLogger()

        logger.log_response(
            {"statusCode": 200, "body": json.dumps({"success": True})}, 15.0
        )

        mock_logger_class.return_value.info.assert_called_once()
