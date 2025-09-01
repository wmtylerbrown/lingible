# Client SDK Regeneration Guide

This guide explains how to regenerate the client SDK while preserving custom code.

## Custom Files Protection

The following files contain custom code and are **automatically protected** by `.openapi-generator-ignore`:

### 🔒 Protected Files:
- `python/lingible_client/auth.py` - Custom Cognito JWT authenticator
- `python/lingible_client/authenticated_client.py` - High-level authenticated client wrapper
- `python/test_lingible_client.py` - Custom test script

## Regeneration Process

### Option 1: Using the Automated Script (Recommended)

```bash
cd client-sdk
./regenerate-sdk.sh
```

### Option 2: Manual Regeneration

```bash
cd client-sdk
openapi-generator generate \
  -i ../shared/api/openapi/lingible-api.yaml \
  -g python \
  -o python \
  --package-name lingible_client \
  --additional-properties=projectName=lingible-client,packageVersion=1.0.0
```

## How Protection Works

The `.openapi-generator-ignore` file contains:
```
# Lingible Custom Files - DO NOT OVERWRITE
lingible_client/auth.py
lingible_client/authenticated_client.py
test_lingible_client.py
requirements.txt
test-requirements.txt
```

This tells the OpenAPI generator to skip these files during regeneration, preserving your custom code automatically.

## Current Custom Code Summary

### auth.py
- `CognitoAuthenticator` class for AWS Cognito JWT authentication
- Handles token refresh and validation
- Used by authenticated_client.py

### authenticated_client.py
- `AuthenticatedLingibleClient` class wrapping the generated client
- Automatically handles authentication headers
- Provides convenient methods for all API endpoints
- Uses auth.py for Cognito authentication

### test_lingible_client.py
- Comprehensive test script for the client
- Tests authentication, translation, user endpoints
- Demonstrates proper usage patterns

## Post-Regeneration Checklist

- [ ] No import errors in custom files
- [ ] Test script runs without errors: `cd python && python test_lingible_client.py`
- [ ] Authentication flow works
- [ ] API endpoints accessible (no /v1 prefix)
- [ ] All custom functionality preserved

## Requirements Files

Both `requirements.txt` and `test-requirements.txt` are now protected by `.openapi-generator-ignore` to preserve any custom dependency versions or additions specific to our project.
