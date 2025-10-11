# 🚀 Lingible Infrastructure

AWS CDK infrastructure for the Lingible mobile application backend.

## 📋 Overview

This project contains the complete infrastructure for Lingible, including:
- **DynamoDB Tables**: Users, translations, and trending data
- **Cognito User Pool**: Authentication with Apple Sign-In
- **Lambda Functions**: API handlers and background processing
- **API Gateway**: REST API with custom domain
- **Route 53**: DNS management with hosted zones
- **CloudWatch**: Monitoring and alerting
- **SNS**: Notifications
- **S3 + CloudFront**: Static website hosting

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Mobile App    │    │   API Gateway   │    │   Lambda        │
│                 │◄──►│   (Custom Domain)│◄──►│   Functions     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                       │
                                ▼                       ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │   Cognito       │    │   DynamoDB      │
                       │   User Pool     │    │   Tables        │
                       └─────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- AWS CLI configured with appropriate permissions
- Node.js and npm installed
- Apple Developer account with Sign-In capability

### First Time Setup

```bash
# 1. Install dependencies
npm install

# 2. Configure credentials
# Edit shared/config/backend/dev.json and prod.json with your credentials

# 3. Store secrets securely
npm run secrets create apple-private-key dev
npm run secrets create apple-iap-private-key dev
npm run secrets create tavily-api-key dev  # Get API key from https://tavily.com

# 4. Deploy hosted zones (DNS)
npm run deploy:hosted-zones:dev

# 5. Add NS records to Squarespace DNS
# (Use the output from step 4)

# 6. Deploy full infrastructure
npm run deploy:dev
```

### Regular Deployment

```bash
# Deploy changes to development
npm run deploy:dev

# Deploy to production
npm run deploy:prod
```

## 🔐 Credential Management

### Apple Sign-In Setup

The infrastructure uses Apple Sign-In for authentication. Credentials are split for security:

**Non-sensitive credentials** (stored in `shared/config/backend/dev.json` and `prod.json`):
- Client ID
- Team ID
- Key ID

**Sensitive credentials** (stored in AWS Secrets Manager):
- Private Key (for Cognito Apple Sign-In)
- IAP Private Key (for App Store Server API and receipt validation)

### Tavily API Setup

The infrastructure uses Tavily for web search during slang validation. The API key is stored securely:

**Sensitive credentials** (stored in AWS Secrets Manager):
- Tavily API Key (for web search in slang validation)

**Configuration** (stored in `shared/config/backend/dev.json` and `prod.json`):
- `slang_validation.web_search_enabled`: Enable/disable web search
- `slang_validation.max_search_results`: Number of search results to analyze

### Managing Credentials

```bash
# List all secrets for an environment
npm run secrets list dev
npm run secrets list prod

# Create/update secrets
npm run secrets create apple-private-key dev
npm run secrets create apple-iap-private-key dev
npm run secrets create tavily-api-key dev  # Get from https://tavily.com

# Update existing secrets
npm run secrets update apple-private-key dev
npm run secrets update tavily-api-key dev

# Check secret status
npm run secrets info apple-private-key dev
npm run secrets info tavily-api-key dev

# Delete secrets (if needed)
npm run secrets delete apple-private-key dev
npm run secrets delete tavily-api-key dev
```

**Note**: Credentials in `shared/config/backend/dev.json` and `prod.json` should be updated with your actual values before deployment.

## 📁 Project Structure

```
infrastructure/
├── app.ts                    # Main CDK application
├── utils/
│   └── config-loader.ts      # Shared config loader
├── scripts/
│   ├── manage-secrets.js     # Unified secret management (Apple, Tavily, etc.)
│   ├── get-dns-info.js       # DNS information utility
│   └── build-lambda-packages.js # Lambda packaging
├── constructs/
│   ├── backend_stack.ts      # Main infrastructure stack
│   ├── hosted_zones_stack.ts # DNS infrastructure
│   └── website_stack.ts      # Website infrastructure
├── stacks/
│   └── lingible_stack.ts     # Stack composition
```

## 🛠️ Available Commands

### Infrastructure Deployment
```bash
npm run deploy:dev                    # Deploy full development environment (backend + website)
npm run deploy:prod                   # Deploy full production environment (backend + website)
npm run deploy:hosted-zones:dev       # Deploy DNS only for development
npm run deploy:hosted-zones:prod      # Deploy DNS only for production
```

### Deployment Modes
The same `app.ts` file handles both deployment modes:
- **DNS Only**: `--context deploy-backend=false` - Deploys only hosted zones for DNS setup
- **Full Stack**: `--context deploy-backend=true` (default) - Deploys backend + website (references existing hosted zones)

**Important**: Hosted zones must be deployed first before the full stack can be deployed.

### Stack Architecture
- **Lingible-Dev**: Main backend stack (API, Lambda, DynamoDB, Cognito)
- **Lingible-Dev-Website**: Website stack (S3, CloudFront, Route53)
- **Lingible-Dev-HostedZones**: DNS stack (Route53 hosted zones)

### Secret Management
```bash
npm run secrets list <env>                        # List all secrets
npm run secrets create <secret-type> <env>        # Create a secret
npm run secrets update <secret-type> <env>        # Update a secret
npm run secrets info <secret-type> <env>          # Get secret info
npm run secrets delete <secret-type> <env>        # Delete a secret

# Secret types: apple-private-key, apple-iap-private-key, tavily-api-key
```

### Development
```bash
npm run build                         # Build TypeScript and Lambda packages
npm run cdk:synth                    # Synthesize CloudFormation
npm run cdk:diff                     # Show deployment changes
npm run lint                         # Run linter
```

### Utility
```bash
npm run get-dns-info                 # Get DNS information
npm run build-lambda-packages        # Build Lambda packages
npm run clean                        # Clean build artifacts
npm run python:test                  # Run Python tests
npm run python:lint                  # Run Python linter
npm run python:type-check            # Run Python type checking
```

## 🔧 Configuration

### Environment Variables

- `CDK_DEFAULT_ACCOUNT`: AWS account ID
- `CDK_DEFAULT_REGION`: AWS region (default: us-east-1)

### Configuration File

Update `shared/config/environments/dev.json` and `prod.json` with your credentials:

```json
{
  "dev": {
    "apple": {
      "clientId": "com.lingible.lingible.dev",
      "teamId": "YOUR_TEAM_ID",
      "keyId": "YOUR_KEY_ID"
    }
  },
  "prod": {
    "apple": {
      "clientId": "com.lingible.lingible",
      "teamId": "YOUR_TEAM_ID",
      "keyId": "YOUR_KEY_ID"
    }
  }
}
```

## 🚨 Troubleshooting

### Common Issues

**"Secret not found" error**
```bash
# List all secrets to see what's missing
npm run secrets list dev

# Check specific secrets
npm run secrets info apple-private-key dev
npm run secrets info apple-iap-private-key dev
npm run secrets info tavily-api-key dev

# Create missing secrets
npm run secrets create apple-private-key dev
npm run secrets create apple-iap-private-key dev
npm run secrets create tavily-api-key dev
```

**"TO_BE_SET" in Cognito configuration**
- Ensure you've created the private key secret
- Check that `shared/config/backend/dev.json` and `prod.json` are properly configured

**Slang validation not using web search**
- Ensure Tavily API key is stored: `npm run secrets info tavily-api-key dev`
- Check `web_search_enabled` is set to `true` in `shared/config/backend/dev.json`
- Verify the API key is valid at https://tavily.com

**DNS issues**
- Verify NS records are added to Squarespace DNS
- Check hosted zones deployment output

**Build errors**
```bash
npm run clean  # Clean build artifacts
npm install    # Reinstall dependencies
```

## 🔒 Security

- ✅ Sensitive credentials stored in AWS Secrets Manager (Apple keys, Tavily API key)
- ✅ Private keys never embedded in CloudFormation templates
- ✅ Configuration files gitignored
- ✅ Environment-specific secrets (dev/prod isolation)
- ✅ All traffic through API Gateway (no direct AWS access)
- ✅ IAM permissions scoped to specific secrets

## 📊 Monitoring

The infrastructure includes:
- CloudWatch dashboards for API metrics
- Lambda function monitoring
- DynamoDB table metrics
- SNS notifications for alerts


## 📝 Development

### Adding New Services

1. Create new construct in `constructs/`
2. Add to `LingibleStack` in `stacks/lingible_stack.ts`
3. Update documentation

### Lambda Functions

Lambda functions are automatically packaged with:
- Individual handler code
- Dependencies layer (Python packages from poetry)
- Shared code layer (common Python modules)
- Smart change detection for fast deployments
- Optimized build process (no unnecessary local package installation)

## 📄 License

This project is part of the Lingible application.
