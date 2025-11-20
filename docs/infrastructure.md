# Infrastructure Deployment

This document describes the CDK infrastructure stacks and deployment process for Lingible.

**Stack Structure**: The infrastructure uses a single `BackendStack` that combines all backend resources (Lambda layers, DynamoDB tables, SNS topics, Cognito, API Gateway) to avoid CloudFormation cross-stack reference issues. Logical separation is maintained through internal constructs. The `WebsiteStack` remains separate as it has no dependencies.

## Stack Architecture

The infrastructure is organized into two CloudFormation stacks:

- **`BackendStack`**: Combined stack containing all backend resources (deployed as one stack to avoid cross-stack reference issues)
- **`WebsiteStack`**: CloudFront distribution, S3 static site hosting (independent, no dependencies)

### Backend Stack Structure

The `BackendStack` uses internal constructs to maintain logical separation while deploying as a single stack:

**Construct Organization**:
```
BackendStack (single CloudFormation stack)
├── SharedConstruct (Lambda layers)
│   ├── Core layer
│   ├── Shared code layer
│   ├── Receipt validation layer
│   └── Slang validation layer
├── DataConstruct (DynamoDB tables, S3 buckets)
│   ├── Users table
│   ├── Translations table
│   ├── Submissions table
│   ├── Lexicon table
│   ├── Trending table
│   └── Lexicon S3 bucket
├── AsyncConstruct (SNS topics, async Lambdas)
│   ├── Alert topic
│   ├── Slang submissions topic
│   ├── Validation request topic
│   └── Async Lambda functions
└── ApiConstruct (Cognito, API Gateway, API Lambdas)
    ├── Cognito user pool
    ├── API Gateway
    ├── API Lambda functions
    └── CloudWatch monitoring
```

**Why Single Stack?**
- Avoids CloudFormation cross-stack reference issues (e.g., Lambda layer updates)
- All resources deploy atomically
- No dependency management complexity
- Logical separation maintained through constructs

**Construct Location**: All constructs are in `backend/cdk/src/constructs/`:
- `shared-construct.ts` → `SharedConstruct`
- `data-construct.ts` → `DataConstruct`
- `async-construct.ts` → `AsyncConstruct`
- `api-construct.ts` → `ApiConstruct`

**WebsiteStack** is independent with no dependencies and can be deployed separately.

## Deployment Prerequisites

### Required Tools
- **Node.js**: For CDK and npm scripts
- **Docker Desktop**: Required for Lambda layer bundling (ARM64)
- **Python 3.11+**: For Lambda runtime and Poetry
- **AWS CLI**: Configured with appropriate credentials

### Environment Setup

```bash
# Install CDK dependencies
cd backend/cdk
npm install

# Install Python dependencies
cd ../lambda
poetry install
```

## Deployment Process

### 1. Build Assets

Before deploying, build all assets:

```bash
cd backend/cdk
npm run build              # TypeScript compilation
npm run build:lambdas      # Lambda layers and packages
npm run build:website     # Static website bundle
```

**Note**: The `presynth`, `prediff`, and `predeploy` scripts automatically run these build steps.

### 2. Synthesize Stack

Generate CloudFormation templates:

```bash
# Development
npm run synth:dev

# Production
npm run synth:prod
```

**Docker Required**: Lambda bundling requires Docker Desktop to be running.

### 3. Review Changes

Compare with deployed stack:

```bash
npm run diff:dev    # Development
npm run diff:prod   # Production
```

### 4. Deploy Stack

Deploy to AWS:

```bash
npm run deploy:dev    # Development
npm run deploy:prod   # Production
```

**Deployment Order**:
1. `BackendStack` - All backend resources deploy together (constructs created in order: Shared → Data → Async → Api)
2. `WebsiteStack` - Independent, can deploy in parallel or separately

**Note**: Since all backend resources are in a single stack, there are no cross-stack dependencies to manage. The constructs are instantiated in the correct order within the stack.

### 5. Manual DNS Configuration

After deployment, configure DNS manually in Squarespace:

1. **API Domain**: Copy `ApiManualDNSInstructions` from CDK outputs
   - Create CNAME record pointing to API Gateway domain
   - Add ACM validation records when requested

2. **Auth Domain**: Copy `AuthManualDNSInstructions` from CDK outputs
   - Create CNAME record pointing to Cognito CloudFront endpoint
   - Add ACM validation records when requested

3. **Website Domain**: Copy website DNS instructions from CDK outputs
   - Create CNAME record pointing to CloudFront distribution
   - Add ACM validation records when requested

**Note**: Route53 hosted zones are not used to reduce costs. All DNS is managed manually in Squarespace.

## Environment Configuration

### Environment Variables

CDK reads configuration from:
- `shared/config/infrastructure/dev.json` (development)
- `shared/config/infrastructure/prod.json` (production)

### Secrets Management

**SSM Parameter Store** (preferred):
- `/lingible/{env}/secrets/apple-iap-private-key`
- `/lingible/{env}/secrets/tavily-api-key`

**Secrets Manager** (Cognito only):
- `lingible-apple-private-key-{env}`

**Management Script**:
```bash
cd backend/cdk
npm run secrets create apple-iap-private-key dev
npm run secrets update tavily-api-key prod
npm run secrets list dev
```

See `docs/security.md` for detailed secrets management.

## Lambda Configuration

### Environment Variables

Each Lambda function receives only the environment variables it needs via `LambdaEnvironmentBuilder`:

```typescript
buildLambdaEnvironment({ ctx, data })
  .includeTables()        // DynamoDB table names
  .includeUsageLimits()   // Tier limit configuration
  .includeApple()         // Apple IAP config paths
  .includeLlm()           // Bedrock configuration
  .includeSnsTopics()     // SNS topic ARNs
  .build()
```

### IAM Permissions

**Least Privilege**: Each Lambda only gets permissions for:
- DynamoDB tables it accesses (read/write)
- SSM parameters it needs (explicit paths)
- SNS topics it publishes to
- S3 buckets it accesses

**No Wildcard Policies**: All IAM policies are scoped to specific resources.

## DynamoDB Tables

All tables are provisioned in the `DataConstruct` (within `BackendStack`):

| Table | Purpose | TTL | PITR |
| --- | --- | --- | --- |
| `UsersTable` | User profiles, usage, quiz sessions | Per-item | Yes |
| `TranslationsTable` | Translation history | Per-item | Yes |
| `SubmissionsTable` | User slang submissions | Optional | Yes |
| `LexiconTable` | Canonical lexicon entries | None | Yes |
| `TrendingTable` | Trending analytics | 90 days | Yes |

See `docs/database-schema.md` for complete table and index definitions.

## Monitoring

### CloudWatch Logs

All Lambda functions log to:
- `/aws/lambda/{function-name}`

**Retention**: 7 days (default), 30 days for critical functions

### CloudWatch Metrics

- API Gateway: Request count, latency, error rates
- Lambda: Invocation count, duration, errors, throttles
- DynamoDB: Read/write capacity, throttles

### X-Ray Tracing

Optional distributed tracing (configurable per environment).

## Troubleshooting

### Docker Not Running

**Error**: `docker: Cannot connect to the Docker daemon`
**Solution**: Start Docker Desktop before running `synth` or `deploy`

### Build Failures

**Error**: `tsc: command not found`
**Solution**: Run `npm install` in `backend/cdk` directory

### Deployment Failures

**Error**: Stack deployment fails
**Solution**:
1. Check CloudFormation events in AWS Console
2. Review CloudWatch logs for Lambda function errors
3. Verify secrets/parameters exist in SSM/Secrets Manager

### Stack Update Issues

**Issue**: Stack update fails or resources don't update
**Solution**:
1. All backend resources are in a single stack, so no cross-stack dependency issues
2. If update fails, check CloudFormation events for specific resource errors
3. Verify construct references are correct in `backend-stack.ts`
4. Try `cdk deploy --force` to force updates

### DNS Validation

**Error**: ACM certificate validation fails
**Solution**:
1. Copy DNS validation records from CDK outputs
2. Add CNAME records in Squarespace
3. Wait for validation (can take several minutes)

## Cleanup

### Remove All Stacks

```bash
cd backend/cdk
npm run destroy:dev    # Development
npm run destroy:prod   # Production
```

**Warning**: This will delete all resources including DynamoDB tables and data.

### Clean Build Artifacts

```bash
cd backend/cdk
npm run clean
```

Removes: `cdk.out`, `dist`, `artifacts`, `node_modules`, `website/build`

## Best Practices

1. **Always build before deploy**: Use `presynth`/`predeploy` scripts
2. **Review diffs**: Run `diff` before deploying to production
3. **Test in dev first**: Deploy to dev environment before production
4. **Monitor deployments**: Watch CloudFormation events during deployment
5. **Keep secrets secure**: Never commit secrets to version control
6. **Document DNS changes**: Keep track of manual DNS configurations
