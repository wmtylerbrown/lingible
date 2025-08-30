# Handlers Directory Structure

This directory contains all Lambda handlers organized by functionality for independent building and deployment.

## 📁 Directory Structure

### **API Handlers** (Public API endpoints)
- **`translate_api/`** - Translation API endpoint (`POST /translate`)
- **`user_profile_api/`** - User profile API endpoint (`GET /user/profile`)
- **`user_usage_api/`** - User usage API endpoint (`GET /user/usage`)
- **`user_upgrade_api/`** - User upgrade API endpoint (`POST /user/upgrade`)
- **`health_api/`** - Health check API endpoint (`GET /health`)
- **`translation_history_api/`** - Translation history API endpoints (premium users only)
  - `get_translation_history.py` - `GET /translations` - Get translation history
  - `delete_translation.py` - `DELETE /translations/{id}` - Delete specific translation
  - `delete_all_translations.py` - `DELETE /translations` - Delete all translations

### **Webhook Handlers** (External service callbacks)
- **`apple_webhook/`** - Apple subscription webhook handler

### **Authentication & Authorization**
- **`authorizer/`** - API Gateway Lambda authorizer (JWT validation)

### **Cognito Triggers** (User lifecycle events)
- **`cognito_post_confirmation/`** - User creation after email confirmation
- **`cognito_pre_authentication/`** - User validation before login
- **`cognito_pre_user_deletion/`** - Data cleanup before account deletion

### **Background Processing**
- **`user_data_cleanup/`** - Comprehensive user data cleanup

## 🏗️ **Independent Building**

Each handler directory contains:
- **`__init__.py`** - Package initialization
- **Handler file(s)** - Main Lambda function code

### **Benefits of This Structure:**
1. **Independent Deployment** - Each handler can be built/deployed separately
2. **Clear Separation** - API handlers vs triggers vs background jobs
3. **Shared Dependencies** - Common requirements in `core-requirements.txt`
4. **Easier Testing** - Test individual handlers in isolation
5. **Better CI/CD** - Build only changed handlers

## 📦 **Dependencies**

### **Core Requirements** (`core-requirements.txt`)
- `aws-lambda-powertools` - Lambda framework
- `boto3` - AWS SDK
- `pydantic` - Data validation
- `PyJWT` - JWT handling
- `cryptography` - Cryptographic operations
- `requests` - HTTP requests

### **Dependencies**
All handlers use the same requirements from `requirements.txt`.

## 🚀 **Building Individual Handlers**

### **Example: Build Translation API Handler**
```bash
cd handlers/translate_api
# Dependencies are installed at project level
# Build handler package
```

### **Example: Build All API Handlers**
```bash
# Install dependencies once at project level
pip install -r handlers/requirements.txt

# Build handlers
for dir in handlers/*_api; do
  echo "Building $dir..."
  cd $dir
  # Build handler package
  cd ../..
done
```

## 🔧 **Deployment**

Each handler can be deployed independently to different Lambda functions or as part of a larger deployment package.

### **Recommended Deployment Strategy:**
1. **API Handlers** - Deploy together (same API Gateway)
2. **Cognito Triggers** - Deploy individually (different trigger points)
3. **Background Jobs** - Deploy separately (different execution contexts)
4. **Authorizer** - Deploy independently (shared across APIs)

## 📝 **Adding New Handlers**

1. Create new directory: `handlers/new_handler_name/`
2. Add `__init__.py` file
3. Add handler code
4. Update this README

## 🎯 **Current Status**

- ✅ **API Handlers**: 6/6 complete
- ✅ **Webhook Handlers**: 1/1 complete
- ✅ **Authorizer**: 1/1 complete
- ✅ **Cognito Triggers**: 3/3 complete
- ✅ **Background Jobs**: 1/1 complete

**Total: 14/14 handlers organized and ready for independent building!**
