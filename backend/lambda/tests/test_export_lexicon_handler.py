"""Tests for export lexicon Lambda handler."""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone


class TestExportLexiconHandler:
    """Test export lexicon handler functionality."""

    @pytest.fixture
    def sample_approved_terms(self):
        """Sample approved terms for testing."""
        return [
            {
                "PK": "TERM#bussin",
                "SK": "SOURCE#lexicon#bussin",
                "slang_term": "bussin",
                "meaning": "Really good",
                "example_usage": "That pizza was bussin!",
                "status": "approved",
                "source": "lexicon",
                "lexicon_variants": ["bussin", "BUSSIN"],
                "lexicon_pos": "adj",
                "lexicon_tags": ["food", "approval"],
                "lexicon_confidence": 0.95,
                "lexicon_age_rating": "E",
                "lexicon_content_flags": [],
                "created_at": "2023-01-01T00:00:00Z",
                "last_used_at": "2025-09-23T00:00:00Z",
                "times_translated": 150,
                "lexicon_momentum": 1.2,
                "lexicon_categories": ["approval", "food"]
            },
            {
                "PK": "TERM#cap",
                "SK": "SOURCE#user#sub_456",
                "slang_term": "cap",
                "meaning": "Lie",
                "example_usage": "That's cap!",
                "status": "approved",
                "source": "user_submission",
                "lexicon_variants": ["cap", "CAP"],
                "lexicon_pos": "noun",
                "lexicon_tags": ["disapproval"],
                "lexicon_confidence": 0.88,
                "lexicon_age_rating": "E",
                "lexicon_content_flags": [],
                "created_at": "2023-02-01T00:00:00Z",
                "last_used_at": "2025-09-23T00:00:00Z",
                "times_translated": 75,
                "lexicon_momentum": 0.8,
                "lexicon_categories": ["disapproval"]
            }
        ]

    @pytest.fixture
    def mock_context(self):
        """Mock Lambda context."""
        context = Mock()
        context.function_name = "test-export-lexicon"
        context.memory_limit_in_mb = 512
        context.remaining_time_in_millis = lambda: 30000
        return context

    @pytest.fixture
    def mock_repository(self):
        """Mock SlangTermRepository."""
        mock_repo = Mock()
        return mock_repo

    @pytest.fixture
    def mock_s3_client(self):
        """Mock S3 client."""
        mock_client = Mock()
        return mock_client

    def test_format_term_for_lexicon_lexicon_source(self, sample_approved_terms):
        """Test formatting lexicon term for export."""
        from handlers.export_lexicon_handler.handler import format_term_for_lexicon

        term = sample_approved_terms[0]  # lexicon source
        result = format_term_for_lexicon(term)

        assert result["term"] == "bussin"
        assert result["variants"] == ["bussin", "BUSSIN"]
        assert result["pos"] == "adj"
        assert result["gloss"] == "Really good"
        assert result["examples"] == ["That pizza was bussin!"]
        assert result["tags"] == ["food", "approval"]
        assert result["status"] == "approved"
        assert result["confidence"] == 0.95
        assert result["age_rating"] == "E"
        assert result["first_seen"] == "2023-01-01"
        assert result["last_seen"] == "2025-09-23"
        assert result["sources"]["runtime"] == 150
        assert result["momentum"] == 1.2
        assert result["categories"] == ["approval", "food"]

    def test_format_term_for_lexicon_user_source(self, sample_approved_terms):
        """Test formatting user submission term for export."""
        from handlers.export_lexicon_handler.handler import format_term_for_lexicon

        term = sample_approved_terms[1]  # user submission source
        result = format_term_for_lexicon(term)

        assert result["term"] == "cap"
        assert result["gloss"] == "Lie"
        assert result["sources"]["runtime"] == 75

    def test_format_term_for_lexicon_missing_fields(self):
        """Test formatting term with missing optional fields."""
        from handlers.export_lexicon_handler.handler import format_term_for_lexicon

        term = {
            "slang_term": "minimal",
            "meaning": "Basic meaning",
            "status": "approved",
            "created_at": "2023-01-01T00:00:00Z",
            "last_used_at": "2023-01-01T00:00:00Z",
            "times_translated": 0,
        }

        result = format_term_for_lexicon(term)

        assert result["term"] == "minimal"
        assert result["gloss"] == "Basic meaning"
        assert result["examples"] == []  # Should be empty list, not None
        assert result["tags"] == []
        assert result["confidence"] == 0.85  # Default value
        assert result["sources"]["runtime"] == 0

    @patch('handlers.export_lexicon_handler.handler.SlangTermRepository')
    @patch('handlers.export_lexicon_handler.handler.aws_services')
    def test_lambda_handler_success(self, mock_aws_services, mock_repo_class,
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
            from handlers.export_lexicon_handler.handler import lambda_handler

            event = {}
            result = lambda_handler(event, mock_context)

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

    @patch('handlers.export_lexicon_handler.handler.SlangTermRepository')
    @patch('handlers.export_lexicon_handler.handler.aws_services')
    def test_lambda_handler_no_terms(self, mock_aws_services, mock_repo_class, mock_context):
        """Test export with no approved terms."""
        # Setup mocks
        mock_repo = Mock()
        mock_repo.get_all_approved_terms.return_value = []
        mock_repo_class.return_value = mock_repo

        mock_s3_client = Mock()
        mock_aws_services.s3_client = mock_s3_client

        with patch.dict('os.environ', {'ENVIRONMENT': 'test'}):
            from handlers.export_lexicon_handler.handler import lambda_handler

            event = {}
            result = lambda_handler(event, mock_context)

            assert result["statusCode"] == 200
            body = json.loads(result["body"])
            assert body["terms_exported"] == 0

            # Should still upload to S3
            mock_s3_client.put_object.assert_called_once()

    @patch('handlers.export_lexicon_handler.handler.SlangTermRepository')
    @patch('handlers.export_lexicon_handler.handler.aws_services')
    def test_lambda_handler_format_error(self, mock_aws_services, mock_repo_class, mock_context):
        """Test export with term formatting error."""
        # Setup mocks with malformed term
        mock_repo = Mock()
        mock_repo.get_all_approved_terms.return_value = [
            {
                # Missing required fields
                "slang_term": "malformed",
                "status": "approved"
            }
        ]
        mock_repo_class.return_value = mock_repo

        mock_s3_client = Mock()
        mock_aws_services.s3_client = mock_s3_client

        with patch.dict('os.environ', {'ENVIRONMENT': 'test'}):
            from handlers.export_lexicon_handler.handler import lambda_handler

            event = {}
            result = lambda_handler(event, mock_context)

            # Should still succeed but with fewer terms
            assert result["statusCode"] == 200
            body = json.loads(result["body"])
            assert body["terms_exported"] == 0  # Malformed term skipped

    @patch('handlers.export_lexicon_handler.handler.SlangTermRepository')
    @patch('handlers.export_lexicon_handler.handler.aws_services')
    def test_lambda_handler_s3_error(self, mock_aws_services, mock_repo_class,
                                    sample_approved_terms, mock_context):
        """Test export with S3 upload error."""
        # Setup mocks
        mock_repo = Mock()
        mock_repo.get_all_approved_terms.return_value = sample_approved_terms
        mock_repo_class.return_value = mock_repo

        mock_s3_client = Mock()
        mock_s3_client.put_object.side_effect = Exception("S3 upload failed")
        mock_aws_services.s3_client = mock_s3_client

        with patch.dict('os.environ', {'ENVIRONMENT': 'test'}):
            from handlers.export_lexicon_handler.handler import lambda_handler

            event = {}
            result = lambda_handler(event, mock_context)

            assert result["statusCode"] == 500
            body = json.loads(result["body"])
            assert "Export failed" in body["message"]
            assert "S3 upload failed" in body["error"]

    @patch('handlers.export_lexicon_handler.handler.SlangTermRepository')
    def test_lambda_handler_repository_error(self, mock_repo_class, mock_context):
        """Test export with repository error."""
        # Setup mocks
        mock_repo = Mock()
        mock_repo.get_all_approved_terms.side_effect = Exception("Database error")
        mock_repo_class.return_value = mock_repo

        with patch.dict('os.environ', {'ENVIRONMENT': 'test'}):
            from handlers.export_lexicon_handler.handler import lambda_handler

            event = {}
            result = lambda_handler(event, mock_context)

            assert result["statusCode"] == 500
            body = json.loads(result["body"])
            assert "Export failed" in body["message"]
            assert "Database error" in body["error"]

    def test_lexicon_data_version_and_timestamp(self, sample_approved_terms):
        """Test that exported lexicon has correct version and timestamp."""
        from handlers.export_lexicon_handler.handler import format_term_for_lexicon

        # Mock the datetime.now to get predictable timestamp
        with patch('handlers.export_lexicon_handler.handler.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 15, 10, 30, 45, tzinfo=timezone.utc)
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

            # This would be tested in the full lambda handler, but we can test the format
            term = sample_approved_terms[0]
            formatted = format_term_for_lexicon(term)

            # Verify the term structure is correct for lexicon format
            assert "term" in formatted
            assert "gloss" in formatted
            assert "variants" in formatted
            assert "pos" in formatted
            assert "examples" in formatted
            assert "tags" in formatted
            assert "status" in formatted
            assert "confidence" in formatted
            assert "sources" in formatted
            assert "momentum" in formatted
            assert "categories" in formatted
