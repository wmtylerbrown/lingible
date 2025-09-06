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

# 2. Configure Apple credentials
# Edit shared/config/environments/dev.json and prod.json with your Apple credentials

# 3. Store Apple secrets securely
npm run apple-secret create private-key dev
npm run apple-secret create shared-secret dev

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

**Non-sensitive credentials** (stored in `shared/config/environments/dev.json` and `prod.json`):
- Client ID
- Team ID
- Key ID

**Sensitive credentials** (stored in AWS Secrets Manager):
- Private Key (for Cognito Apple Sign-In)
- Shared Secret (for App Store receipt validation)

### Managing Credentials

```bash
# Store/update private key (for Cognito Apple Sign-In)
npm run apple-secret create private-key dev
npm run apple-secret update private-key dev

# Store/update shared secret (for App Store receipt validation)
npm run apple-secret create shared-secret dev
npm run apple-secret update shared-secret dev

# Check secret status
npm run apple-secret info private-key dev
npm run apple-secret info shared-secret dev

# Delete secrets (if needed)
npm run apple-secret delete private-key dev
npm run apple-secret delete shared-secret dev
```

**Note**: Apple credentials in `shared/config/environments/dev.json` and `prod.json` should be updated with your actual values before deployment.

## 📁 Project Structure

```
infrastructure/
├── app.ts                    # Main CDK application
├── utils/
│   └── config-loader.ts      # Shared config loader
├── scripts/
│   ├── manage-apple-secret.js # Apple secret management
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
npm run apple-secret create private-key <env>     # Create Apple private key
npm run apple-secret create shared-secret <env>   # Create Apple shared secret
npm run apple-secret update private-key <env>     # Update Apple private key
npm run apple-secret update shared-secret <env>   # Update Apple shared secret
npm run apple-secret info private-key <env>       # Check private key status
npm run apple-secret info shared-secret <env>     # Check shared secret status
npm run apple-secret delete private-key <env>     # Delete Apple private key
npm run apple-secret delete shared-secret <env>   # Delete Apple shared secret
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
npm run apple-secret info private-key dev  # Check if private key exists
npm run apple-secret info shared-secret dev  # Check if shared secret exists
npm run apple-secret create private-key dev  # Create private key if missing
npm run apple-secret create shared-secret dev  # Create shared secret if missing
```

**"TO_BE_SET" in Cognito configuration**
- Ensure you've created the private key secret
- Check that `shared/config/environments/dev.json` and `prod.json` are properly configured

**DNS issues**
- Verify NS records are added to Squarespace DNS
- Check hosted zones deployment output

**Build errors**
```bash
npm run clean  # Clean build artifacts
npm install    # Reinstall dependencies
```

## 🔒 Security

- ✅ Apple private keys stored in AWS Secrets Manager
- ✅ Private keys never embedded in CloudFormation templates
- ✅ Configuration file gitignored
- ✅ Environment-specific secrets
- ✅ All traffic through API Gateway (no direct AWS access)

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
