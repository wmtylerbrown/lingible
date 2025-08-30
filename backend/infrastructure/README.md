# Lingible Infrastructure

This directory contains the AWS CDK infrastructure code for Lingible.

## 🏗️ Architecture Overview

The infrastructure is organized into modular stacks:

```
LingibleStack (Main Stack)
├── DatabaseStack
│   ├── Users Table (Single-table design)
│   └── Translations Table
├── CognitoStack
│   ├── User Pool
│   ├── User Pool Client
│   ├── Identity Pool
│   └── IAM Roles
├── LambdaStack
│   ├── API Handlers
│   ├── Cognito Triggers
│   ├── Authorizer
│   └── Background Processing
├── ApiGatewayStack
│   ├── REST API
│   ├── Lambda Authorizer
│   ├── Endpoints
│   └── Usage Plans
└── MonitoringStack
    ├── CloudWatch Dashboard
    ├── Alarms
    └── SNS Notifications
```

## 🚀 Quick Start

### Prerequisites

1. **AWS CLI** configured with appropriate credentials
2. **Node.js** (for CDK CLI)
3. **Python 3.11+**
4. **CDK CLI** installed globally

```bash
npm install -g aws-cdk
```

### Installation

1. **Navigate to infrastructure directory:**
   ```bash
   cd backend/infrastructure
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Apple Identity Provider (optional):**
   ```bash
   python setup-apple-provider.py
   ```

4. **Deploy to Development:**
   ```bash
   python deploy-dev.py
   ```

5. **Deploy to Production:**
   ```bash
   python deploy-prod.py
   ```

   Or manually with context:
   ```bash
   # Development
   cdk deploy --context environment=dev

   # Production
   cdk deploy --context environment=prod
   ```

## 📁 File Structure

```
infrastructure/
├── app.py                          # Main CDK app entry point
├── deploy.py                       # Deployment script
├── requirements.txt                # CDK dependencies
├── README.md                       # This file
├── stacks/
│   └── lingible_stack.py          # Main orchestration stack
└── constructs/
    ├── database_stack.py           # DynamoDB tables
    ├── cognito_stack.py            # User authentication
    ├── lambda_stack.py             # Lambda functions
    ├── api_gateway_stack.py        # API Gateway
    └── monitoring_stack.py         # CloudWatch monitoring
```

## 🗄️ Database Design

### DynamoDB Tables

| Table | Purpose | Partition Key | Sort Key | GSIs |
|-------|---------|---------------|-----------|------|
| `lingible-users` | User profiles, subscriptions, and usage (Single-table design) | `PK: USER#{user_id}` | `SK: PROFILE/USAGE/SUBSCRIPTION` | Email, Username, Subscription Status, Transaction ID, Usage Tier |
| `lingible-translations` | Translation history | `PK: USER#{user_id}` | `SK: TRANSLATION#{id}` | Direction, Model |

### Data Access Patterns

- **User Lookups**: By user ID, email, or username
- **Translation History**: By user ID with pagination
- **Subscription Status**: By user ID and subscription ID (in users table)
- **Usage Tracking**: By user ID with daily/monthly resets (in users table)

## 🔐 Authentication & Authorization

### Cognito User Pool

- **Self-signup enabled** with email verification
- **Sign in with Apple** integration for seamless authentication
- **Custom attributes** for user tier and subscription
- **MFA optional** (SMS and TOTP)
- **Password policy** with complexity requirements
- **Device tracking** for security

### Lambda Authorizer

- **JWT validation** using Cognito tokens
- **User context injection** into Lambda functions
- **Token caching** (5 minutes) for performance
- **Automatic user ID extraction** for handlers

## 🚀 Lambda Functions

### API Handlers

| Function | Purpose | Endpoint | Auth Required |
|----------|---------|-----------|---------------|
| `translate` | Text translation | `POST /translate` | ✅ |
| `user-profile` | User profile data | `GET /user/profile` | ✅ |
| `user-usage` | Usage statistics | `GET /user/usage` | ✅ |
| `user-upgrade` | Subscription upgrade | `POST /user/upgrade` | ✅ |
| `translation-history` | Get translations | `GET /translations` | ✅ |
| `delete-translation` | Delete translation | `DELETE /translations/{id}` | ✅ |
| `delete-all-translations` | Clear history | `DELETE /translations` | ✅ |
| `health` | Health check | `GET /health` | ❌ |

### Cognito Triggers

| Function | Trigger | Purpose |
|----------|---------|---------|
| `post-confirmation` | Post Confirmation | Create user record |
| `pre-authentication` | Pre Authentication | Ensure user exists |
| `pre-user-deletion` | Pre User Deletion | Cleanup user data |

### Background Processing

| Function | Purpose | Trigger |
|----------|---------|---------|
| `user-data-cleanup` | Comprehensive cleanup | Manual/SQS |

## 🌐 API Gateway

### Endpoints

- **Public**: Health check, webhooks
- **Authenticated**: All user and translation endpoints
- **CORS enabled** for cross-origin requests
- **Rate limiting** (1000 req/min, 500 burst)
- **Usage plans** with API keys

### Lambda Authorizer

- **Custom authorizer** for JWT validation
- **User context injection** into Lambda events
- **Performance optimized** with caching

## 📊 Monitoring & Alerting

### CloudWatch Dashboard

- **Lambda metrics**: Duration, errors, invocations
- **API Gateway metrics**: Request count, errors, latency
- **DynamoDB metrics**: Capacity units, throttling, errors
- **Business metrics**: Custom widgets for KPIs

### Alarms

- **Lambda errors**: >5 errors in 5 minutes
- **Lambda duration**: >25 seconds average
- **API Gateway errors**: >10 5XX errors in 5 minutes
- **API Gateway latency**: >5 seconds average
- **DynamoDB throttling**: >10 throttled requests in 5 minutes

### SNS Notifications

- **Centralized alerting** via SNS topic
- **Email subscriptions** (configure for production)
- **Integration** with PagerDuty, Slack, etc.

## 🔧 Configuration

### Environment Variables

All Lambda functions receive these environment variables:

```bash
POWERTOOLS_SERVICE_NAME=lingible
LOG_LEVEL=INFO
USERS_TABLE=lingible-users
TRANSLATIONS_TABLE=lingible-translations
USER_POOL_ID=<cognito-user-pool-id>
USER_POOL_CLIENT_ID=<cognito-client-id>
IDENTITY_POOL_ID=<cognito-identity-pool-id>
```

### IAM Permissions

- **DynamoDB access** to all tables and indexes
- **CloudWatch Logs** for logging
- **X-Ray** for tracing
- **Cognito** access for user management

## 🚀 Deployment

### Development Environment

```bash
cd backend/infrastructure
python deploy-dev.py
```

**Development Resources:**
- Stack: `Lingible-Dev`
- Tables: `lingible-users-dev`, `lingible-translations-dev`
- API Gateway: `lingible-api-dev`
- Cognito: `lingible-users-dev`
- Stage: `dev`

### Production Environment

```bash
cd backend/infrastructure
python deploy-prod.py
```

**Production Resources:**
- Stack: `Lingible-Prod`
- Tables: `lingible-users-prod`, `lingible-translations-prod`
- API Gateway: `lingible-api-prod`
- Cognito: `lingible-users-prod`
- Stage: `prod`

**Production Checklist:**
- ✅ Environment-specific resource naming
- ✅ Proper IAM roles and policies
- ✅ Monitoring and alerting configured
- ✅ Security settings reviewed
- ⚠️ Configure Apple Identity Provider if needed
- ⚠️ Set up SNS email subscriptions for alerts

### Manual Deployment

```bash
# Development
cdk deploy --context environment=dev

# Production
cdk deploy --context environment=prod --require-approval any-change
```

## 🧪 Testing

### Local Testing

```bash
# Synthesize CloudFormation template
cdk synth

# View diff before deployment
cdk diff

# Validate template
cdk validate
```

### Integration Testing

1. **Deploy infrastructure**
2. **Test Cognito user creation**
3. **Test API endpoints with authentication**
4. **Verify monitoring and alerting**

## 📈 Scaling

### Auto-scaling Features

- **DynamoDB**: On-demand billing with auto-scaling
- **Lambda**: Automatic scaling based on demand
- **API Gateway**: Built-in scaling and throttling

### Performance Optimization

- **Lambda authorizer caching** (5 minutes)
- **DynamoDB GSIs** for efficient queries
- **Connection pooling** in Lambda functions
- **X-Ray tracing** for performance analysis

## 🔒 Security

### Data Protection

- **Encryption at rest** (DynamoDB)
- **Encryption in transit** (HTTPS)
- **IAM roles** with least privilege
- **VPC isolation** (if needed)

### Access Control

- **JWT-based authentication**
- **User-scoped data access**
- **API rate limiting**
- **Audit logging**

## 💰 Cost Optimization

### Cost-effective Design

- **DynamoDB on-demand** billing
- **Lambda pay-per-use** model
- **API Gateway** tiered pricing
- **CloudWatch** basic monitoring

### Cost Monitoring

- **AWS Cost Explorer** integration
- **Resource tagging** for cost allocation
- **Usage alerts** via CloudWatch
- **Optimization recommendations**

## 🚨 Troubleshooting

### Common Issues

1. **CDK Bootstrap Required**
   ```bash
   cdk bootstrap
   ```

2. **Permission Denied**
   - Check AWS credentials
   - Verify IAM permissions

3. **Lambda Timeout**
   - Increase timeout in `lambda_config`
   - Check DynamoDB performance

4. **CORS Issues**
   - Update CORS configuration in API Gateway
   - Check origin allowlist

### Debug Commands

```bash
# View CloudFormation events
cdk deploy --verbose

# Check Lambda logs
aws logs tail /aws/lambda/lingible-translate

# Test API endpoint
curl -X GET https://<api-id>.execute-api.<region>.amazonaws.com/prod/health
```

## 📚 Additional Resources

- [AWS CDK Documentation](https://docs.aws.amazon.com/cdk/)
- [Lambda Powertools](https://awslabs.github.io/aws-lambda-powertools-python/)
- [DynamoDB Best Practices](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/best-practices.html)
- [Cognito Developer Guide](https://docs.aws.amazon.com/cognito/latest/developerguide/)

## 🤝 Contributing

1. **Follow CDK best practices**
2. **Add tests** for new constructs
3. **Update documentation** for changes
4. **Use conventional commits** for commit messages

## 📄 License

This infrastructure code is part of the Lingible project.
