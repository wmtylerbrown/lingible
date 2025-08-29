# Style Guide - GenZ Slang Translation App

## Python Code Style

### General Principles
- **Readability**: Code should be self-documenting and easy to understand
- **Consistency**: Follow established patterns throughout the codebase
- **Type Safety**: Use type hints for all functions, methods, and variables
- **Error Handling**: Explicit error handling with proper exception types
- **Documentation**: Comprehensive docstrings for all public APIs

### Code Formatting
- **Black**: Use Black for automatic code formatting
- **Line Length**: 88 characters maximum (Black default)
- **Indentation**: 4 spaces (no tabs)
- **Trailing Whitespace**: No trailing whitespace
- **File Encoding**: UTF-8

### Import Organization
```python
# Standard library imports
import json
import logging
from typing import Dict, List, Optional

# Third-party imports
import boto3
from aws_lambda_powertools import Logger, Tracer
from pydantic import BaseModel, Field

# Local imports
from src.models.users import User, UserProfile
from src.services.user_service import UserService
from src.utils.response import create_response
```

### Naming Conventions

#### Files and Modules
- **Files**: snake_case (e.g., `user_service.py`, `translation_handler.py`)
- **Modules**: snake_case (e.g., `user_service`, `translation_handler`)
- **Packages**: snake_case (e.g., `src`, `handlers`, `services`)

#### Classes
- **Class Names**: PascalCase (e.g., `UserService`, `TranslationHandler`)
- **Exception Classes**: PascalCase with "Error" suffix (e.g., `UserNotFoundError`)
- **Abstract Classes**: PascalCase with "Base" prefix (e.g., `BaseRepository`)

#### Functions and Methods
- **Function Names**: snake_case (e.g., `get_user_profile`, `translate_text`)
- **Method Names**: snake_case (e.g., `create_user`, `validate_translation`)
- **Private Methods**: snake_case with leading underscore (e.g., `_validate_input`)

#### Variables and Constants
- **Variables**: snake_case (e.g., `user_id`, `translation_result`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `MAX_TRANSLATIONS_PER_DAY`)
- **Class Variables**: snake_case (e.g., `default_timeout`)
- **Instance Variables**: snake_case (e.g., `self.user_id`)

#### Type Variables
- **Generic Type Variables**: PascalCase (e.g., `T`, `UserType`)
- **Type Aliases**: snake_case (e.g., `user_dict = Dict[str, Any]`)

## Pydantic Models

### Model Definition
```python
from pydantic import BaseModel, Field, validator
from typing import Optional, List

class UserProfile(BaseModel):
    """User profile information."""
    
    user_id: str = Field(..., description="Unique user identifier")
    display_name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., regex=r"^[^@]+@[^@]+\.[^@]+$")
    tier: UserTier = Field(default=UserTier.FREE)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('display_name')
    def validate_display_name(cls, v: str) -> str:
        """Validate display name format."""
        if not v.strip():
            raise ValueError("Display name cannot be empty")
        return v.strip()
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
```

### Field Definitions
- **Required Fields**: Use `Field(...)` for required fields
- **Optional Fields**: Use `Optional[Type]` with default values
- **Field Validation**: Use `Field()` with validation parameters
- **Field Descriptions**: Always provide descriptive field descriptions

### Model Configuration
- **JSON Encoders**: Define custom JSON encoders for complex types
- **Alias Generation**: Use camelCase for API responses
- **Extra Fields**: Configure extra field handling (forbid, ignore, allow)

## Type Hints

### Function Signatures
```python
from typing import Dict, List, Optional, Union

def get_user_profile(user_id: str) -> Optional[UserProfile]:
    """Get user profile by ID."""
    pass

def translate_text(
    text: str,
    source_language: str,
    target_language: str,
    user_id: Optional[str] = None
) -> TranslationResult:
    """Translate text between languages."""
    pass

def create_user(
    user_data: Dict[str, Any],
    tier: UserTier = UserTier.FREE
) -> User:
    """Create a new user."""
    pass
```

### Variable Annotations
```python
# Explicit type annotations
user_id: str = "user123"
translation_count: int = 0
is_active: bool = True
user_tier: UserTier = UserTier.FREE

# Complex types
user_profiles: List[UserProfile] = []
translation_history: Dict[str, List[TranslationResult]] = {}
```

### Generic Types
```python
from typing import TypeVar, Generic

T = TypeVar('T')

class Repository(Generic[T]):
    """Generic repository interface."""
    
    def get(self, id: str) -> Optional[T]:
        pass
    
    def save(self, entity: T) -> T:
        pass
```

## Error Handling

### Exception Hierarchy
```python
class AppError(Exception):
    """Base application exception."""
    
    def __init__(self, message: str, error_code: str = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code

class ValidationError(AppError):
    """Validation error."""
    pass

class UserNotFoundError(AppError):
    """User not found error."""
    pass

class TranslationError(AppError):
    """Translation service error."""
    pass
```

### Error Handling Patterns
```python
def get_user_profile(user_id: str) -> UserProfile:
    """Get user profile with proper error handling."""
    try:
        user = user_repository.get(user_id)
        if not user:
            raise UserNotFoundError(f"User {user_id} not found")
        return user
    except UserNotFoundError:
        # Re-raise user-specific errors
        raise
    except Exception as e:
        # Log and wrap unexpected errors
        logger.error(f"Unexpected error getting user {user_id}: {e}")
        raise AppError("Internal server error") from e
```

## Logging

### Logger Configuration
```python
import logging
from aws_lambda_powertools import Logger

# Configure structured logging
logger = Logger(
    service="translation-app",
    level=logging.INFO,
    correlation_id_path="$.requestContext.requestId"
)
```

### Logging Patterns
```python
# Business events
logger.info("User translation completed", extra={
    "user_id": user_id,
    "translation_id": translation_id,
    "source_language": source_lang,
    "target_language": target_lang,
    "character_count": len(text)
})

# Error logging
logger.error("Translation service error", extra={
    "user_id": user_id,
    "error": str(error),
    "error_code": error.error_code
})

# Debug information
logger.debug("Processing translation request", extra={
    "text_length": len(text),
    "user_tier": user.tier.value
})
```

## Documentation

### Docstrings
```python
def translate_text(
    text: str,
    source_language: str,
    target_language: str,
    user_id: Optional[str] = None
) -> TranslationResult:
    """
    Translate text between specified languages using AWS Bedrock.
    
    Args:
        text: The text to translate
        source_language: Source language code (e.g., 'en', 'es')
        target_language: Target language code (e.g., 'en', 'es')
        user_id: Optional user ID for usage tracking
        
    Returns:
        TranslationResult: The translation result with metadata
        
    Raises:
        ValidationError: If input validation fails
        TranslationError: If translation service fails
        UsageLimitExceededError: If user exceeds usage limits
    """
    pass
```

### Module Documentation
```python
"""
Translation service module.

This module provides translation functionality using AWS Bedrock.
It handles text translation between different languages with usage
tracking and rate limiting.

Classes:
    TranslationService: Main translation service class
    
Functions:
    translate_text: Translate text between languages
    
Exceptions:
    TranslationError: Translation service errors
    UsageLimitExceededError: Usage limit exceeded errors
"""
```

## Testing

### Test Structure
```python
import pytest
from unittest.mock import Mock, patch
from src.services.translation_service import TranslationService

class TestTranslationService:
    """Test cases for TranslationService."""
    
    @pytest.fixture
    def translation_service(self):
        """Create translation service instance for testing."""
        return TranslationService()
    
    @pytest.fixture
    def mock_bedrock_client(self):
        """Mock AWS Bedrock client."""
        with patch('boto3.client') as mock_client:
            yield mock_client
    
    def test_translate_text_success(self, translation_service, mock_bedrock_client):
        """Test successful text translation."""
        # Arrange
        text = "Hello world"
        source_lang = "en"
        target_lang = "es"
        
        # Act
        result = translation_service.translate_text(text, source_lang, target_lang)
        
        # Assert
        assert result.translated_text == "Hola mundo"
        assert result.source_language == source_lang
        assert result.target_language == target_lang
```

### Test Naming
- **Test Classes**: `Test{ClassName}` (e.g., `TestTranslationService`)
- **Test Methods**: `test_{method_name}_{scenario}` (e.g., `test_translate_text_success`)
- **Test Files**: `test_{module_name}.py` (e.g., `test_translation_service.py`)

## AWS Service Integration

### Service Client Patterns
```python
import boto3
from typing import Optional

class AWSServiceManager:
    """Centralized AWS service management."""
    
    def __init__(self):
        self._bedrock_client: Optional[Any] = None
        self._dynamodb_client: Optional[Any] = None
    
    @property
    def bedrock_client(self) -> Any:
        """Get Bedrock client with lazy initialization."""
        if self._bedrock_client is None:
            self._bedrock_client = boto3.client('bedrock-runtime')
        return self._bedrock_client
    
    @property
    def dynamodb_client(self) -> Any:
        """Get DynamoDB client with lazy initialization."""
        if self._dynamodb_client is None:
            self._dynamodb_client = boto3.client('dynamodb')
        return self._dynamodb_client
```

### Configuration Management
```python
from aws_lambda_powertools.utilities.parameters import get_parameter

class Config:
    """Application configuration management."""
    
    @staticmethod
    def get_bedrock_model() -> str:
        """Get Bedrock model name from SSM."""
        return get_parameter('/translation-app/bedrock-model', force_fetch=True)
    
    @staticmethod
    def get_max_translations_per_day() -> int:
        """Get max translations per day from SSM."""
        return int(get_parameter('/translation-app/max-translations-per-day', force_fetch=True))
```

## Performance Guidelines

### Lambda Optimization
- **Cold Start**: Minimize imports and use lazy loading
- **Memory**: Right-size memory allocation for cost/performance
- **Timeout**: Set appropriate timeout values
- **Dependencies**: Minimize deployment package size

### Database Optimization
- **Query Patterns**: Design for efficient DynamoDB queries
- **Indexing**: Use GSIs strategically
- **Batch Operations**: Use batch operations when possible
- **Connection Management**: Reuse connections efficiently

### Caching Strategy
- **Application Cache**: Cache frequently accessed data
- **TTL Management**: Set appropriate cache TTL
- **Cache Invalidation**: Implement proper cache invalidation
- **Cache Monitoring**: Monitor cache hit/miss ratios

## Security Guidelines

### Input Validation
- **Type Validation**: Validate all input types
- **Length Validation**: Validate string lengths
- **Format Validation**: Validate data formats (email, etc.)
- **Content Validation**: Validate content for malicious input

### Authentication
- **Token Validation**: Properly validate JWT tokens
- **User Context**: Extract and validate user context
- **Authorization**: Implement proper authorization checks
- **Session Management**: Secure session handling

### Data Protection
- **Sensitive Data**: Never log sensitive information
- **Data Encryption**: Encrypt sensitive data at rest
- **Secure Communication**: Use HTTPS for all communications
- **Access Control**: Implement proper access controls
