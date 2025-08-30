# Lingible

A comprehensive mobile application project with AWS-powered backend infrastructure using API Gateway and individual Lambda handlers.

## Project Structure

```
lingible/
├── backend/                 # AWS Backend API
│   ├── src/                # Lambda function source code
│   │   ├── handlers/       # Individual Lambda handlers
│   │   ├── models/         # Pydantic models
│   │   ├── services/       # Business logic
│   │   └── utils/          # Shared utilities
│   ├── tests/              # Unit and integration tests
│   └── infrastructure/     # AWS CDK infrastructure
├── mobile/                 # Mobile applications (iOS/Android)
│   ├── react-native/       # React Native app
│   └── flutter/           # Flutter app
└── docs/                  # Documentation
```

## Backend Architecture

The backend uses AWS serverless architecture with individual Lambda handlers:

- **API Gateway**: RESTful API endpoints with individual routes
- **Lambda Functions**: One handler per API path/endpoint
- **DynamoDB**: NoSQL database for data storage
- **Cognito**: User authentication and authorization
- **S3**: File storage
- **CloudWatch**: Monitoring and logging
- **AWS CDK**: Infrastructure as Code

## API Endpoints Structure

Each API endpoint has its own Lambda handler:

```
/api/
├── auth/
│   ├── login
│   ├── register
│   └── refresh
├── users/
│   ├── profile
│   ├── update
│   └── delete
├── data/
│   ├── list
│   ├── create
│   ├── get/{id}
│   ├── update/{id}
│   └── delete/{id}
└── files/
    ├── upload
    ├── download/{id}
    └── delete/{id}
```

## Quick Start

### Prerequisites
- Node.js 18+ and npm
- AWS CLI configured
- Python 3.9+ (for Lambda functions)
- AWS CDK CLI installed

### Backend Setup
```bash
cd backend
pip install -r requirements.txt
cd infrastructure
npm install
```

### Deploy Infrastructure
```bash
cd backend/infrastructure
npm run build
cdk deploy
```

### Mobile Setup
Choose your framework:

**React Native:**
```bash
cd mobile/react-native
npm install
npx react-native run-ios  # or run-android
```

**Flutter:**
```bash
cd mobile/flutter
flutter pub get
flutter run
```

## Development Workflow

1. **Lambda Development**: Create new handlers in `backend/src/handlers/`
2. **Infrastructure**: Update CDK stack in `backend/infrastructure/`
3. **Testing**: Run tests for individual handlers
4. **Deployment**: Deploy with `cdk deploy`
5. **Mobile Development**: Choose React Native or Flutter

## Environment Variables

Create `.env` files in each subdirectory as needed:

```bash
# Backend
AWS_REGION=us-east-1
AWS_PROFILE=default

# Mobile
API_BASE_URL=https://your-api-gateway-url.amazonaws.com
```

## Contributing

1. Create feature branches
2. Write tests for new functionality
3. Update documentation
4. Submit pull requests

## License

MIT License - see LICENSE file for details
