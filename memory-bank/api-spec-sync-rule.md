# CRITICAL RULE: OpenAPI Spec Synchronization

## 🚨 MANDATORY REQUIREMENT

**The OpenAPI specification MUST ALWAYS be kept in sync with the actual backend API implementation.**

> **SEE ALSO**: `CRITICAL_API_RULE.md` in this same directory for a concise version of this rule.

## 📋 What Must Be Updated

Whenever ANY of the following changes are made to the backend API, the OpenAPI spec MUST be updated immediately:

### 1. **API Endpoints**
- New endpoints added
- Endpoint paths changed (e.g., adding `/v1/` prefix)
- HTTP methods changed
- Endpoint removed

### 2. **Request Models**
- New required fields added
- Field names changed
- Field types changed
- Field validation rules changed
- Optional fields made required (or vice versa)

### 3. **Response Models**
- Response field names changed
- New response fields added
- Response structure changed
- Error response formats changed

### 4. **Authentication**
- Authentication method changed
- Header names changed
- Token format changed
- Authorization requirements changed

### 5. **API Versioning**
- Version prefixes added/changed
- Backward compatibility changes

## 📁 File Location

**Primary Spec File**: `shared/api/openapi/lingible-api.yaml`

## ⚡ Update Process

1. **Make backend changes**
2. **IMMEDIATELY update OpenAPI spec** to match
3. **Test the spec** against actual endpoints
4. **Regenerate client SDKs** if needed
5. **Update documentation** if needed

## 🎯 Why This Matters

- **Client SDKs** are generated from the spec
- **API documentation** comes from the spec
- **Contract testing** relies on the spec
- **Frontend integration** depends on accurate spec
- **Third-party integrations** use the spec

## ❌ Consequences of Out-of-Sync Spec

- Generated clients fail to work
- Documentation becomes incorrect
- Integration issues
- Wasted development time debugging
- Poor developer experience

## ✅ Success Criteria

The OpenAPI spec is considered up-to-date when:
- All endpoints in the spec match actual backend endpoints
- All request/response models match actual backend models
- All field names and types are accurate
- All authentication requirements are correct
- Generated clients work without modification

## 🔄 Regular Maintenance

- Review spec weekly for accuracy
- Test generated clients against actual API
- Update spec before any API changes
- Validate spec changes in development environment

---

**This rule is NON-NEGOTIABLE and must be followed for every API change.**
