"""Tests for export lexicon async handler."""

import pytest
import json
import os
from unittest.mock import Mock, patch
from datetime import datetime, timezone

from models.slang import (
    SlangTerm,
    PartOfSpeech,
    ApprovalStatus,
    AgeRating,
    QuizCategory,
    QuizDifficulty,
)


class TestExportLexiconAsyncHandler:
    """Test export lexicon async handler functionality."""

    @pytest.fixture
    def sample_approved_terms(self):
        """Sample approved terms for testing."""
        return [
            SlangTerm(
                term="bussin",
                gloss="Really good",
                variants=["bussin", "BUSSIN"],
                pos=PartOfSpeech.ADJECTIVE,
                examples=["That pizza was bussin!"],
                tags=["food", "approval"],
                status=ApprovalStatus.APPROVED,
                confidence=0.95,
                regions=[],
                age_rating=AgeRating.EVERYONE,
                content_flags=[],
                first_seen="2023-01-01",
                last_seen="2025-09-23",
                sources={"reddit": 0, "youtube": 0, "runtime": 150},
                momentum=1.2,
                categories=["approval", "food"],
                first_attested="2020-05-15",
                first_attested_confidence="high",
                attestation_note="Test attestation note",
                is_quiz_eligible=True,
                quiz_category=QuizCategory.APPROVAL,
                quiz_difficulty=QuizDifficulty.BEGINNER,
            ),
            SlangTerm(
                term="cap",
                gloss="Lie",
                variants=["cap", "CAP"],
                pos=PartOfSpeech.NOUN,
                examples=["That's cap!"],
                tags=["disapproval"],
                status=ApprovalStatus.APPROVED,
                confidence=0.88,
                regions=[],
                age_rating=AgeRating.EVERYONE,
                content_flags=[],
                first_seen="2023-02-01",
                last_seen="2025-09-23",
                sources={"runtime": 75},
                momentum=0.8,
                categories=["disapproval"],
                is_quiz_eligible=True,
                quiz_category=QuizCategory.DISAPPROVAL,
                quiz_difficulty=QuizDifficulty.BEGINNER,
            ),
        ]

    @pytest.fixture(autouse=True)
    def set_required_env(self):
        with patch.dict(
            os.environ,
            {
                "TERMS_TABLE": "test-terms-table",
                "LEXICON_S3_BUCKET": "lingible-slang-lexicon-test",
                "LEXICON_S3_KEY": "lexicon.json",
                "ENVIRONMENT": "test",
            },
        ):
            # Ensure repository cache is cleared between tests
            try:
                # Import only when needed to avoid circular dependencies
                import handlers.export_lexicon_async.handler as handler_module
                handler_module._repository_instance = None
                yield
            finally:
                try:
                    handler_module._repository_instance = None
                except NameError:
                    pass  # Module not imported yet

    @pytest.fixture
    def mock_context(self):
        """Mock Lambda context."""
        context = Mock()
        context.function_name = "test-export-lexicon"
        context.memory_limit_in_mb = 512
        context.remaining_time_in_millis = lambda: 30000
        return context

    @patch('handlers.export_lexicon_async.handler.LexiconRepository')
    @patch('handlers.export_lexicon_async.handler.aws_services')
    def test_handler_success(self, mock_aws_services, mock_repo_class,
                                   sample_approved_terms, mock_context):
        """Test successful lexicon export."""
        # Setup mocks
        mock_repo = Mock()
        mock_repo.get_all_approved_terms.return_value = sample_approved_terms
        mock_repo_class.return_value = mock_repo

        mock_s3_client = Mock()
        mock_aws_services.s3_client = mock_s3_client

        # Mock environment
        with patch.dict('os.environ', {'ENVIRONMENT': 'test'}):
            from handlers.export_lexicon_async.handler import handler

            event = {}
            result = handler(event, mock_context)

            # Verify response
            assert result["statusCode"] == 200
            body = json.loads(result["body"])
            assert body["message"] == "Lexicon exported successfully"
            assert body["terms_exported"] == 2
            assert body["bucket"] == "lingible-slang-lexicon-test"
            assert body["version"] == "3.0-dynamic"

            # Verify S3 upload
            mock_s3_client.put_object.assert_called_once()
            call_args = mock_s3_client.put_object.call_args
            assert call_args[1]["Bucket"] == "lingible-slang-lexicon-test"
            assert call_args[1]["Key"] == "lexicon.json"
            assert call_args[1]["ContentType"] == "application/json"
            assert call_args[1]["CacheControl"] == "public, max-age=3600"

            # Verify lexicon data structure
            uploaded_data = json.loads(call_args[1]["Body"])
            assert uploaded_data["version"] == "3.0-dynamic"
            assert uploaded_data["count"] == 2
            assert len(uploaded_data["items"]) == 2
            assert uploaded_data["items"][0]["term"] == "bussin"
            assert uploaded_data["items"][1]["term"] == "cap"

    @patch('handlers.export_lexicon_async.handler.LexiconRepository')
    @patch('handlers.export_lexicon_async.handler.aws_services')
    def test_handler_no_terms(self, mock_aws_services, mock_repo_class, mock_context):
        """Test export with no approved terms."""
        # Setup mocks
        mock_repo = Mock()
        mock_repo.get_all_approved_terms.return_value = []
        mock_repo_class.return_value = mock_repo

        mock_s3_client = Mock()
        mock_aws_services.s3_client = mock_s3_client

        # Clear the cached repository instance before importing handler
        import handlers.export_lexicon_async.handler as handler_module
        handler_module._repository_instance = None

        from handlers.export_lexicon_async.handler import handler

        event = {}
        result = handler(event, mock_context)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["terms_exported"] == 0

        # Should still upload to S3
        mock_s3_client.put_object.assert_called_once()

    @patch('handlers.export_lexicon_async.handler.LexiconRepository')
    @patch('handlers.export_lexicon_async.handler.aws_services')
    def test_handler_s3_error(self, mock_aws_services, mock_repo_class,
                                    sample_approved_terms, mock_context):
        """Test export with S3 upload error."""
        # Setup mocks
        mock_repo = Mock()
        mock_repo.get_all_approved_terms.return_value = sample_approved_terms
        mock_repo_class.return_value = mock_repo

        mock_s3_client = Mock()
        mock_s3_client.put_object.side_effect = Exception("S3 upload failed")
        mock_aws_services.s3_client = mock_s3_client

        # Clear the cached repository instance before importing handler
        import handlers.export_lexicon_async.handler as handler_module
        handler_module._repository_instance = None

        from handlers.export_lexicon_async.handler import handler

        event = {}
        result = handler(event, mock_context)

        assert result["statusCode"] == 500
        body = json.loads(result["body"])
        assert "Export failed" in body["message"]
        assert "S3 upload failed" in body["error"]

    @patch('handlers.export_lexicon_async.handler.LexiconRepository')
    @patch('handlers.export_lexicon_async.handler.aws_services')
    def test_handler_repository_error(self, mock_aws_services, mock_repo_class, mock_context):
        """Test export with repository error."""
        # Setup mocks
        mock_repo = Mock()
        mock_repo.get_all_approved_terms.side_effect = Exception("Database error")
        mock_repo_class.return_value = mock_repo

        mock_s3_client = Mock()
        mock_aws_services.s3_client = mock_s3_client

        # Clear the cached repository instance before importing handler
        import handlers.export_lexicon_async.handler as handler_module
        handler_module._repository_instance = None

        from handlers.export_lexicon_async.handler import handler

        event = {}
        result = handler(event, mock_context)

        assert result["statusCode"] == 500
        body = json.loads(result["body"])
        assert "Export failed" in body["message"]
        assert "Database error" in body["error"]
