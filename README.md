# Lingible

A comprehensive mobile application for translating GenZ slang to English and vice versa, powered by AWS Bedrock AI.

## 🚨 CRITICAL RULE

**⚠️ BEFORE MAKING ANY API CHANGES, READ: [`API_SPEC_RULE.md`](./API_SPEC_RULE.md)**

This rule is MANDATORY and prevents API/client mismatches.

## 🏗️ Architecture

### Backend (AWS Serverless)
- **AWS Lambda** - Python 3.13 serverless functions
- **API Gateway** - REST API endpoints
- **DynamoDB** - Single-table design for data storage
- **AWS Cognito** - User authentication and management
- **AWS Bedrock** - AI translation service
- **AWS CDK** - Infrastructure as Code
- **Poetry** - Modern Python dependency management

### iOS App (Swift/SwiftUI)
- **SwiftUI** - Modern iOS interface
- **Google AdMob** - Monetization for free users
- **StoreKit** - In-app purchases for premium upgrades
- **Amplify** - AWS integration

## 📁 Project Structure

```
lingible/
├── backend/                 # AWS Backend API
│   ├── lambda/             # Python Lambda functions
│   │   ├── src/            # Source code
│   │   │   ├── handlers/   # Individual Lambda handlers
│   │   │   ├── models/     # Pydantic models
│   │   │   ├── services/   # Business logic
│   │   │   ├── repositories/ # Data access layer
│   │   │   └── utils/      # Utility functions
│   │   ├── tests/          # Test suite
│   │   ├── pyproject.toml  # Poetry dependencies
│   │   └── poetry.lock     # Locked dependencies
│   ├── infrastructure/     # AWS CDK infrastructure
│   └── docs/              # Backend documentation
├── ios/                    # iOS Application
│   ├── Lingible/          # Main iOS app
│   ├── generated/         # Generated API client
│   └── scripts/           # iOS build scripts
├── client-sdk/            # Generated client SDKs
│   └── python/           # Python client SDK
├── shared/                # Shared resources
│   ├── api/              # OpenAPI specifications
│   ├── assets/           # Shared assets
│   ├── config/           # Configuration files
│   └── legal/            # Legal documents
├── website/              # Static marketing website
└── memory-bank/          # Project context and documentation
```

## 🚀 Quick Start

### Backend Development
```bash
# Setup Python virtual environment (first time)
python3.13 -m venv .venv
source .venv/bin/activate

# Setup Poetry and dependencies
cd backend
./scripts/setup-poetry.sh   # Setup Poetry (first time)
cd lambda
poetry shell               # Activate Poetry environment
poetry run pytest          # Run tests
```

### iOS Development
```bash
cd ios/Lingible
# Open Lingible.xcodeproj in Xcode
# Follow AdMob integration guide in ADMOB_INTEGRATION.md
```

### Deployment
```bash
cd backend/cdk
npm run deploy:dev         # Deploy to dev environment
npm run deploy:prod        # Deploy to production
```

## 🎯 Key Features

### Translation Engine
- **GenZ ↔ English** bidirectional translation
- **AWS Bedrock** AI-powered translations
- **Usage tracking** with daily limits
- **Translation history** for premium users

### User Management
- **Free Tier**: 10 daily translations, 50 character limit, no history, with ads
- **Premium Tier**: 100 daily translations, 100 character limit, 30-day history, ad-free
- **Daily Reset**: Midnight Central Time
- **Usage Tracking**: Real-time usage monitoring

### Monetization
- **Banner Ads**: Always visible for free users
- **Interstitial Ads**: Every 4th translation
- **Upgrade Prompts**: When daily limit reached
- **Premium Subscription**: Ad-free unlimited usage

## 🔧 Development

### Backend (Poetry + CDK)
- **Dependencies**: Managed with Poetry
- **Build**: CDK uses Docker bundling
- **Testing**: pytest with 90%+ coverage
- **Type Safety**: Full type hints with mypy

### iOS (SwiftUI + AdMob)
- **UI**: Modern SwiftUI interface
- **Ads**: Google AdMob integration
- **API**: Generated Swift client
- **Payments**: StoreKit integration

## 📚 Documentation

- [`API_SPEC_RULE.md`](./API_SPEC_RULE.md) - Critical API development rules
- [`backend/docs/poetry-migration.md`](./backend/docs/poetry-migration.md) - Poetry setup guide
- [`ios/Lingible/ADMOB_INTEGRATION.md`](./ios/Lingible/ADMOB_INTEGRATION.md) - AdMob integration
- [`backend/docs/timezone-change-summary.md`](./backend/docs/timezone-change-summary.md) - Timezone fixes
- [`backend/docs/tier-storage-fix-summary.md`](./backend/docs/tier-storage-fix-summary.md) - Performance optimizations

## 🌐 Environments

- **Development**: `api.dev.lingible.com`
- **Production**: `api.lingible.com`
- **Website**: `lingible.com`

## 📄 License

See [`shared/legal/`](./shared/legal/) for terms and privacy policy.
