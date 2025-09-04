# Enum Usage Rule

## Problem
We keep making the same mistake of using `.value` on string enums, which causes `AttributeError: 'str' object has no attribute 'value'` errors.

## Rule: When to Use `.value` on Enums

### ✅ CORRECT: Use `.value` for Integer Enums
```python
# HTTPStatus is an integer enum
status_code = HTTPStatus.OK.value  # Returns 200
```

### ✅ CORRECT: Use enum directly for String Enums
```python
# UserTier, TrendingCategory, SubscriptionProvider, etc. are string enums
user_tier = UserTier.FREE  # Returns "free" directly
# String enums automatically convert to their string values when used
```

### ✅ CORRECT: Use enum directly for String Enums that inherit from str, Enum
```python
# TranslationDirection, LogLevel, etc. inherit from str, Enum
direction = TranslationDirection.GENZ_TO_ENGLISH  # Returns "genz_to_english" directly
# These also automatically convert to their string values
```

### ❌ WRONG: Don't use `.value` on String Enums
```python
# This causes AttributeError: 'str' object has no attribute 'value'
user_tier = UserTier.FREE.value  # WRONG!
category = TrendingCategory.SLANG.value  # WRONG!
```

## How to Identify Enum Types

### Integer Enums (use `.value`)
```python
class HTTPStatus(Enum):
    OK = 200
    CREATED = 201
```

### String Enums (don't use `.value`)
```python
class UserTier(Enum):
    FREE = "free"
    PREMIUM = "premium"
```

### String Enums with str inheritance (don't use `.value`)
```python
class TranslationDirection(str, Enum):
    GENZ_TO_ENGLISH = "genz_to_english"
    ENGLISH_TO_GENZ = "english_to_genz"
```

## Quick Test
If you're unsure, test it:
```python
# This will work for string enums
print(UserTier.FREE)  # "free"

# This will fail for string enums
print(UserTier.FREE.value)  # AttributeError: 'str' object has no attribute 'value'
```

## Files Fixed
- `backend/lambda/src/services/trending_service.py`
- `backend/lambda/src/repositories/trending_repository.py`
- `backend/lambda/src/repositories/user_repository.py`
- `backend/lambda/src/repositories/subscription_repository.py`
- `backend/lambda/src/repositories/translation_repository.py`
- `backend/lambda/src/handlers/trending_api/handler.py`
- `backend/lambda/src/handlers/user_upgrade_api/handler.py`
- `backend/lambda/src/handlers/apple_webhook/handler.py`

## Prevention
Always check the enum definition before using `.value`. If the enum values are strings, don't use `.value`.
