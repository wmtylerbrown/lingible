# 🚀 Lingible Infrastructure

AWS CDK infrastructure for the Lingible mobile application backend.

## 📋 Overview

This project contains the complete infrastructure for Lingible, including:
- **DynamoDB Tables**: Users and translations data
- **Cognito User Pool**: Authentication with Apple Sign-In
- **Lambda Functions**: API handlers and background processing
- **API Gateway**: REST API with custom domain
- **Route 53**: DNS management with hosted zones
- **CloudWatch**: Monitoring and alerting
- **SNS**: Notifications

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
cp app-config.json.example app-config.json
# Edit app-config.json with your Apple credentials

# 3. Store Apple private key securely
npm run apple-secret create dev

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

**Non-sensitive credentials** (stored in `app-config.json`):
- Client ID
- Team ID
- Key ID

**Sensitive credentials** (stored in AWS Secrets Manager):
- Private Key

### Managing Credentials

```bash
# Store/update private key
npm run apple-secret create dev
npm run apple-secret update dev

# Check secret status
npm run apple-secret info dev

# Delete secret (if needed)
npm run apple-secret delete dev
```

**Note**: `app-config.json` is gitignored and won't be committed to version control.

## 📁 Project Structure

```
infrastructure/
├── app.ts                    # Main CDK application
├── app-config.json           # Application configuration (gitignored)
├── scripts/
│   ├── manage-apple-secret.ts # Apple secret management
│   ├── get-dns-info.js       # DNS information utility
│   └── build-lambda-packages.js # Lambda packaging
├── constructs/
│   ├── backend_stack.ts      # Main infrastructure stack
│   └── hosted_zones_stack.ts # DNS infrastructure
├── stacks/
│   └── lingible_stack.ts     # Stack composition
└── test/                     # Unit tests
```

## 🛠️ Available Commands

### Infrastructure Deployment
```bash
npm run deploy:dev                    # Deploy full development environment
npm run deploy:prod                   # Deploy full production environment
npm run deploy:hosted-zones:dev       # Deploy DNS only for development
npm run deploy:hosted-zones:prod      # Deploy DNS only for production
```

### Deployment Modes
The same `app.ts` file handles both deployment modes:
- **DNS Only**: `--context deploy-backend=false` - Deploys only hosted zones for DNS setup
- **Full Stack**: `--context deploy-backend=true` (default) - Deploys backend (references existing hosted zones)

**Important**: Hosted zones must be deployed first before the full stack can be deployed.

### Secret Management
```bash
npm run apple-secret create <env>     # Create Apple secret
npm run apple-secret update <env>     # Update Apple secret
npm run apple-secret info <env>       # Check secret status
npm run apple-secret delete <env>     # Delete secret
```

### Development
```bash
npm run build                         # Build TypeScript
npm test                             # Run tests
npm run cdk:synth                    # Synthesize CloudFormation
npm run cdk:diff                     # Show deployment changes
npm run lint                         # Run linter
```

### Utility
```bash
npm run get-dns-info                 # Get DNS information
npm run build-lambda-packages        # Build Lambda packages
npm run clean                        # Clean build artifacts
```

## 🔧 Configuration

### Environment Variables

- `CDK_DEFAULT_ACCOUNT`: AWS account ID
- `CDK_DEFAULT_REGION`: AWS region (default: us-east-1)

### Configuration File

Create `app-config.json` with your credentials:

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
npm run apple-secret info dev  # Check if secret exists
npm run apple-secret create dev  # Create if missing
```

**"TO_BE_SET" in Cognito configuration**
- Ensure you've created the private key secret
- Check that `app-config.json` is properly configured

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

## 🧪 Testing

```bash
npm test                    # Run all tests
npm run test:watch         # Watch mode
npm run test:coverage      # Coverage report
```

## 📝 Development

### Adding New Services

1. Create new construct in `constructs/`
2. Add to `LingibleStack` in `stacks/lingible_stack.ts`
3. Update tests in `test/`
4. Update documentation

### Lambda Functions

Lambda functions are automatically packaged with:
- Individual handler code
- Shared layer for common dependencies
- Smart change detection for fast deployments

## 📄 License

This project is part of the Lingible application.
