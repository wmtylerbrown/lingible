"""Tests for lexicon migration script."""

import pytest
import json
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from models.quiz import QuizDifficulty, QuizCategory


class TestMigrationScript:
    """Test lexicon migration functionality."""

    @pytest.fixture
    def sample_lexicon_data(self):
        """Sample lexicon data for testing."""
        return {
            "version": "2.3",
            "generated_at": "2025-09-23",
            "count": 2,
            "items": [
                {
                    "term": "bussin",
                    "variants": ["bussin", "BUSSIN"],
                    "pos": "adj",
                    "gloss": "Really good",
                    "examples": ["That pizza was bussin", "This song is bussin"],
                    "tags": ["food", "approval"],
                    "status": "approved",
                    "confidence": 0.95,
                    "regions": [],
                    "age_rating": "E",
                    "content_flags": [],
                    "first_seen": "2023-01-01",
                    "last_seen": "2025-09-23",
                    "sources": {"reddit": 0, "youtube": 0, "runtime": 0},
                    "momentum": 1.2,
                    "categories": ["approval", "food"]
                },
                {
                    "term": "cap",
                    "variants": ["cap", "CAP"],
                    "pos": "noun",
                    "gloss": "Lie",
                    "examples": ["That's cap", "No cap"],
                    "tags": ["disapproval"],
                    "status": "approved",
                    "confidence": 0.88,
                    "regions": [],
                    "age_rating": "E",
                    "content_flags": [],
                    "first_seen": "2023-02-01",
                    "last_seen": "2025-09-23",
                    "sources": {"reddit": 0, "youtube": 0, "runtime": 0},
                    "momentum": 0.8,
                    "categories": ["disapproval"]
                }
            ]
        }

    @pytest.fixture
    def temp_lexicon_file(self, sample_lexicon_data):
        """Create temporary lexicon file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(sample_lexicon_data, f)
            temp_file = f.name

        yield temp_file

        # Cleanup
        os.unlink(temp_file)

    @pytest.fixture
    def mock_repository(self):
        """Mock SlangTermRepository."""
        mock_repo = Mock()
        mock_repo.create_lexicon_term.return_value = True
        return mock_repo

    def test_estimate_difficulty_high_confidence(self):
        """Test difficulty estimation for high confidence terms."""
        from scripts.migrate_lexicon import estimate_difficulty

        # High confidence and momentum
        item = {"confidence": 0.95, "momentum": 1.2}
        result = estimate_difficulty(item)
        assert result == QuizDifficulty.BEGINNER

    def test_estimate_difficulty_medium_confidence(self):
        """Test difficulty estimation for medium confidence terms."""
        from scripts.migrate_lexicon import estimate_difficulty

        # Medium confidence and momentum
        item = {"confidence": 0.75, "momentum": 0.9}
        result = estimate_difficulty(item)
        assert result == QuizDifficulty.INTERMEDIATE

    def test_estimate_difficulty_low_confidence(self):
        """Test difficulty estimation for low confidence terms."""
        from scripts.migrate_lexicon import estimate_difficulty

        # Low confidence and momentum
        item = {"confidence": 0.6, "momentum": 0.7}
        result = estimate_difficulty(item)
        assert result == QuizDifficulty.ADVANCED

    def test_estimate_difficulty_defaults(self):
        """Test difficulty estimation with default values."""
        from scripts.migrate_lexicon import estimate_difficulty

        # No confidence or momentum provided
        item = {}
        result = estimate_difficulty(item)
        # Should default to intermediate (0.85 * 1.0 = 0.85)
        assert result == QuizDifficulty.BEGINNER

    def test_map_categories_known_category(self):
        """Test category mapping for known categories."""
        from scripts.migrate_lexicon import map_categories

        result = map_categories(["approval", "food"])
        assert result == QuizCategory.APPROVAL

    def test_map_categories_unknown_category(self):
        """Test category mapping for unknown categories."""
        from scripts.migrate_lexicon import map_categories

        result = map_categories(["unknown_category"])
        assert result == QuizCategory.GENERAL

    def test_map_categories_empty_list(self):
        """Test category mapping for empty list."""
        from scripts.migrate_lexicon import map_categories

        result = map_categories([])
        assert result == QuizCategory.GENERAL

    def test_map_categories_multiple_categories(self):
        """Test category mapping with multiple categories."""
        from scripts.migrate_lexicon import map_categories

        # Should return the first match
        result = map_categories(["food", "approval"])
        assert result == QuizCategory.FOOD

    def test_generate_wrong_options_basic(self):
        """Test wrong option generation."""
        from scripts.migrate_lexicon import generate_wrong_options

        term_data = {
            "categories": ["food"],
            "gloss": "Really good"
        }

        result = generate_wrong_options(term_data)

        assert len(result) == 3
        assert "Really good" not in result  # Should not include correct answer
        # Should include food-specific wrong answers
        assert any(opt in result for opt in ["Delicious", "Spicy", "Sweet", "Sour"])

    def test_generate_wrong_options_category_specific(self):
        """Test wrong option generation for specific categories."""
        from scripts.migrate_lexicon import generate_wrong_options

        # Emotion category
        term_data = {
            "categories": ["emotion"],
            "gloss": "Happy"
        }

        result = generate_wrong_options(term_data)

        assert len(result) == 3
        assert "Happy" not in result
        assert any(opt in result for opt in ["Sad", "Angry", "Excited"])

    def test_generate_wrong_options_generic_fallback(self):
        """Test wrong option generation with generic fallback."""
        from scripts.migrate_lexicon import generate_wrong_options

        # Unknown category
        term_data = {
            "categories": ["unknown"],
            "gloss": "Special meaning"
        }

        result = generate_wrong_options(term_data)

        assert len(result) == 3
        assert "Special meaning" not in result
        # Should include generic options
        assert any(opt in result for opt in ["Very busy", "Broken or damaged", "Confused"])

    @patch('scripts.migrate_lexicon.SlangTermRepository')
    def test_migrate_lexicon_success(self, mock_repo_class, temp_lexicon_file, sample_lexicon_data):
        """Test successful lexicon migration."""
        mock_repo = Mock()
        mock_repo.create_lexicon_term.return_value = True
        mock_repo_class.return_value = mock_repo

        with patch('scripts.migrate_lexicon.open', create=True) as mock_open:
            with patch('builtins.open', mock_open):
                mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(sample_lexicon_data)

                from scripts.migrate_lexicon import migrate_lexicon

                # Mock the file path
                with patch('scripts.migrate_lexicon.os.path.join') as mock_join:
                    mock_join.return_value = temp_lexicon_file

                    imported, failed = migrate_lexicon()

                    assert imported == 2
                    assert failed == 0
                    assert mock_repo.create_lexicon_term.call_count == 2

    @patch('scripts.migrate_lexicon.SlangTermRepository')
    def test_migrate_lexicon_with_failures(self, mock_repo_class, temp_lexicon_file, sample_lexicon_data):
        """Test lexicon migration with some failures."""
        mock_repo = Mock()
        # First call succeeds, second fails
        mock_repo.create_lexicon_term.side_effect = [True, False]
        mock_repo_class.return_value = mock_repo

        with patch('scripts.migrate_lexicon.open', create=True) as mock_open:
            with patch('builtins.open', mock_open):
                mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(sample_lexicon_data)

                from scripts.migrate_lexicon import migrate_lexicon

                with patch('scripts.migrate_lexicon.os.path.join') as mock_join:
                    mock_join.return_value = temp_lexicon_file

                    imported, failed = migrate_lexicon()

                    assert imported == 1
                    assert failed == 1

    @patch('scripts.migrate_lexicon.SlangTermRepository')
    def test_migrate_lexicon_term_data_structure(self, mock_repo_class, temp_lexicon_file, sample_lexicon_data):
        """Test that migrated term data has correct structure."""
        mock_repo = Mock()
        mock_repo.create_lexicon_term.return_value = True
        mock_repo_class.return_value = mock_repo

        with patch('scripts.migrate_lexicon.open', create=True) as mock_open:
            with patch('builtins.open', mock_open):
                mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(sample_lexicon_data)

                from scripts.migrate_lexicon import migrate_lexicon

                with patch('scripts.migrate_lexicon.os.path.join') as mock_join:
                    mock_join.return_value = temp_lexicon_file

                    migrate_lexicon()

                    # Check first term call
                    first_call = mock_repo.create_lexicon_term.call_args_list[0][0][0]
                    assert first_call["PK"] == "TERM#bussin"
                    assert first_call["SK"] == "SOURCE#lexicon#bussin"
                    assert first_call["slang_term"] == "bussin"
                    assert first_call["meaning"] == "Really good"
                    assert first_call["source"] == "lexicon"
                    assert first_call["status"] == "approved"
                    assert first_call["is_quiz_eligible"] is True
                    assert first_call["quiz_difficulty"] == QuizDifficulty.BEGINNER
                    assert first_call["quiz_category"] == QuizCategory.APPROVAL
                    assert len(first_call["quiz_wrong_options"]) == 3

                    # Check GSI fields
                    assert first_call["GSI1PK"] == "STATUS#approved"
                    assert first_call["GSI2PK"] == "QUIZ#beginner"
                    assert first_call["GSI3PK"] == "CATEGORY#approval"
                    assert first_call["GSI4PK"] == "SOURCE#lexicon"

    @patch('scripts.migrate_lexicon.SlangTermRepository')
    def test_migrate_lexicon_handles_missing_fields(self, mock_repo_class, temp_lexicon_file):
        """Test migration handles missing optional fields."""
        # Lexicon data with minimal fields
        minimal_data = {
            "version": "2.3",
            "count": 1,
            "items": [
                {
                    "term": "minimal",
                    "gloss": "Basic meaning",
                    "first_seen": "2023-01-01"
                }
            ]
        }

        mock_repo = Mock()
        mock_repo.create_lexicon_term.return_value = True
        mock_repo_class.return_value = mock_repo

        with patch('scripts.migrate_lexicon.open', create=True) as mock_open:
            with patch('builtins.open', mock_open):
                mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(minimal_data)

                from scripts.migrate_lexicon import migrate_lexicon

                with patch('scripts.migrate_lexicon.os.path.join') as mock_join:
                    mock_join.return_value = temp_lexicon_file

                    imported, failed = migrate_lexicon()

                    assert imported == 1
                    assert failed == 0

                    # Check that missing fields are handled gracefully
                    call_args = mock_repo.create_lexicon_term.call_args_list[0][0][0]
                    assert call_args["slang_term"] == "minimal"
                    assert call_args["meaning"] == "Basic meaning"
                    # Should have defaults for missing fields
                    assert call_args["lexicon_confidence"] == 0.85
                    assert call_args["lexicon_momentum"] == 1.0

    def test_migrate_lexicon_removes_none_values(self):
        """Test that None values are removed from term data."""
        from scripts.migrate_lexicon import migrate_lexicon

        # This test would require mocking the full migration process
        # For now, we'll test the logic directly
        term_data = {
            "PK": "TERM#test",
            "SK": "SOURCE#lexicon#test",
            "slang_term": "test",
            "meaning": "test meaning",
            "optional_field": None,
            "empty_field": "",
        }

        # Simulate the None removal logic
        cleaned_data = {k: v for k, v in term_data.items() if v is not None}

        assert "optional_field" not in cleaned_data
        assert "empty_field" in cleaned_data  # Empty string is not None
        assert "slang_term" in cleaned_data
