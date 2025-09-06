# 🚨 CRITICAL: API SPECIFICATION RULE

## ⚠️ MANDATORY - READ BEFORE ANY API CHANGES

**EVERY TIME you modify ANY backend API code, you MUST update the OpenAPI specification.**

## 📍 Location
- **OpenAPI Spec**: `shared/api/openapi/lingible-api.yaml`
- **TypeScript Types**: `shared/api/types/typescript/api.ts`

## 🔄 Required Updates

### When you change backend models:
1. **Update OpenAPI spec** (`lingible-api.yaml`)
2. **Update TypeScript types** (`api.ts`)
3. **Regenerate client SDKs**:
   - Python: `cd client-sdk && ./regenerate-sdk.sh`
   - iOS: `cd ios/generated && openapi-generator generate ...`

### When you add/change API endpoints:
1. **Update OpenAPI spec** with new endpoint
2. **Update TypeScript types** if needed
3. **Regenerate client SDKs**

## ❌ What Happens If You Don't

- **Client SDKs break** (like the `transaction_id` issue we just fixed)
- **Frontend integration fails**
- **API documentation becomes wrong**
- **Wasted debugging time**

## ✅ Success Checklist

Before considering any API change complete:
- [ ] OpenAPI spec updated
- [ ] TypeScript types updated  
- [ ] Client SDKs regenerated
- [ ] All clients work with new API

---

**This rule is NON-NEGOTIABLE. No exceptions.**

