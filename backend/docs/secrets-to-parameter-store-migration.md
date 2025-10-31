# Migrating Secrets from Secrets Manager to Parameter Store

## Current Secrets Inventory

Based on the codebase analysis, you're currently using **3 secrets** in AWS Secrets Manager:

1. **`lingible-apple-private-key-{env}`** - Apple Sign-In private key (used by Cognito)
2. **`lingible-apple-iap-private-key-{env}`** - Apple In-App Purchase private key
3. **`lingible-tavily-api-key-{env}`** - Tavily API key for web search

## Cost Comparison

### Current Costs (Secrets Manager)
- **Storage**: $0.40/month per secret × 3 = **$1.20/month**
- **API calls**: $0.05 per 10,000 calls (usually minimal)
- **Total**: ~**$1.20/month** (mostly storage)

### Proposed Costs (Parameter Store - Standard with SecureString) ✅ BEST OPTION
- **Storage**: **FREE** (Standard tier)
- **API calls**: Free (first 10,000/month, then $0.05 per 10,000)
- **KMS encryption**: Included via `SecureString` type
- **Total**: **$0/month** (unless you exceed 10,000 API calls/month)

**Savings**: **$1.20/month** ($14.40/year) - **100% cost reduction!**

### Alternative: Parameter Store - Advanced (If Needed)
- **Storage**: $0.05/month per parameter × 3 = **$0.15/month**
- **API calls**: $0.05 per 10,000 after first 10,000
- **Total**: ~**$0.15/month**

**Savings**: **$1.05/month** ($12.60/year)

**Note**: Only use Advanced if your secrets exceed 4 KB or you need parameter policies.

### Parameter Store - Standard (Free) ✅ RECOMMENDED
- **Storage**: **FREE**
- **API calls**: Free (first 10,000/month, then $0.05 per 10,000)
- **Max value size**: 4 KB
- **KMS Encryption**: ✅ **YES - Use `SecureString` type for KMS encryption**
- **Limitations**: No parameter policies (expiration, notifications)

**Important**: Standard tier **DOES support KMS encryption** via the `SecureString` parameter type. This is perfect for your secrets!

### Parameter Store - Advanced
- **Storage**: $0.05/month per parameter
- **API calls**: $0.05 per 10,000 after first 10,000
- **Max value size**: 8 KB
- **KMS Encryption**: ✅ Yes (same as Standard SecureString)
- **Additional features**: Parameter policies (expiration, notifications), hierarchical parameters

**Use Advanced only if**: You need > 4 KB values or parameter expiration policies.

## When to Use Each Service

### Use Parameter Store When:
- ✅ Simple key-value secrets that don't need rotation
- ✅ Want to save costs
- ✅ Secrets fit within size limits (8 KB for Advanced)
- ✅ No need for automatic rotation
- ✅ No need for cross-region replication

### Keep Secrets Manager When:
- ⚠️ Secrets need automatic rotation
- ⚠️ Need cross-region replication
- ⚠️ Secrets are integrated with RDS (automatic rotation)
- ⚠️ Need advanced audit logging beyond CloudTrail

## Migration Considerations

### Challenge: CDK Integration

One secret (`lingible-apple-private-key-{env}`) is used directly in CDK:

```typescript
privateKeyValue: cdk.SecretValue.secretsManager(`lingible-apple-private-key-${environment}`, {
  jsonField: 'privateKey',
})
```

**CDK supports Parameter Store**, but syntax differs:

```typescript
// Parameter Store (Advanced - SecureString)
privateKeyValue: cdk.SecretValue.secretsManager(`arn:aws:ssm:${region}:${account}:parameter/lingible-apple-private-key-${environment}`)
// Or use SSM Parameter reference
privateKeyValue: ssm.StringParameter.valueFromLookup(this, `/lingible-apple-private-key-${environment}`)
```

Actually, CDK's `SecretValue` works with SSM parameters directly:

```typescript
privateKeyValue: cdk.SecretValue.ssmSecure(`/lingible/apple-private-key/${environment}`, {
  version: '1' // Optional version
})
```

## Migration Strategy

### Step 1: Migrate Application Secrets (Easy)

These are retrieved via `ConfigService._get_secrets_manager_secret()`:

1. **Tavily API Key** - Simple string secret
2. **Apple IAP Private Key** - Private key string

**Action**: Create Parameter Store equivalents and update `ConfigService`.

### Step 2: Migrate CDK Secret (Requires Testing)

The Cognito Apple provider secret needs CDK integration changes.

**Action**: Update CDK stack to use Parameter Store, test Cognito integration.

## Implementation

### Option A: Migrate All Secrets (Maximum Savings)

**Pros**:
- Save $1.05/month
- Simpler architecture (one service)

**Cons**:
- Need to test CDK Cognito integration
- Lose automatic rotation (if you ever need it)

### Option B: Hybrid Approach (Recommended)

Keep **Apple Sign-In private key** in Secrets Manager (used by CDK/Cognito directly).

Migrate **Tavily API key** and **Apple IAP private key** to Parameter Store.

**Savings**: $0.80/month ($9.60/year) for 2 secrets

**Pros**:
- Lower risk (don't touch CDK integration)
- Still good savings
- Can test Parameter Store with less critical secrets first

### Option C: Keep Everything in Secrets Manager

**Pros**:
- No migration risk
- Better integration with AWS services

**Cons**:
- Higher cost

## Recommendation

**Start with Option B (Hybrid Approach)**:
1. Migrate `tavily-api-key` and `apple-iap-private-key` to Parameter Store
2. Keep `apple-private-key` in Secrets Manager for now (CDK integration)
3. Test thoroughly
4. Consider migrating the CDK secret later if comfortable

This gives you **$0.80/month savings** with minimal risk.

## Next Steps

Would you like me to:
1. Create a migration script to move secrets to Parameter Store?
2. Update `ConfigService` to support both Secrets Manager and Parameter Store?
3. Update CDK to use Parameter Store for the Cognito secret?
4. Create a comparison document showing exact cost savings?
