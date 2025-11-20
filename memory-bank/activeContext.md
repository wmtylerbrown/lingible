# Active Context - Lingible Backend

## Current Documentation Structure

All documentation has been consolidated into the top-level `docs/` directory:

### Core Documentation
- **`docs/architecture.md`** - System architecture, components, and request flows
- **`docs/functions.md`** - All Lambda functions and services with purposes
- **`docs/backend-code.md`** - Code structure, patterns, and organization
- **`docs/database-schema.md`** - Complete DynamoDB table schemas, indexes, and access patterns
- **`docs/repositories.md`** - Repository responsibilities and data access patterns
- **`docs/infrastructure.md`** - CDK stack architecture and deployment process
- **`docs/security.md`** - Security practices, secrets management, authentication
- **`docs/development.md`** - Development environment, testing, code quality
- **`docs/test-strategy.md`** - Testing approach and coverage targets
- **`docs/README.md`** - Documentation index

### Documentation Cleanup (Completed)
- Removed all point-in-time analysis and planning documents
- Consolidated `table-layout.md` and `index-plan.md` into `database-schema.md`
- Merged `backend/docs/` content into main `docs/` directory
- Removed "proposed" language - all docs now describe current implementation

## Current Infrastructure

### CDK Stacks (`backend/cdk/`)
- **`SharedStack`** - Lambda layers
- **`DataStack`** - DynamoDB tables and S3 buckets
- **`AsyncStack`** - SNS topics and async Lambda functions
- **`ApiStack`** - Cognito, API Gateway, API Lambda functions
- **`WebsiteStack`** - CloudFront and S3 static site

### Database Tables
- **`UsersTable`** - User profiles, usage limits, quiz sessions
- **`TranslationsTable`** - Translation history
- **`SubmissionsTable`** - User slang submissions and moderation
- **`LexiconTable`** - Canonical lexicon entries with quiz metadata
- **`TrendingTable`** - Trending analytics (90-day TTL)

See `docs/database-schema.md` for complete schema definitions.

## Development Workflow

### Testing
- All tests in `backend/lambda/tests/` (unified directory after migration from `tests_v2/`)
- Coverage targets: Repositories 90%+, Translation/User/Quiz services 90%+, Others 50%+
- Use `moto` for AWS service mocking
- TDD workflow: Red-Green-Refactor
- 334 tests passing with comprehensive coverage
- Individual test files for each handler, service, and utility module

### Code Quality
- Type safety: All functions must have type hints
- Use Pydantic models (not dicts)
- Enum serialization: Use `str(enum)` not `enum.value`
- Imports at top of file only

### Deployment
- CDK commands: `npm run synth:dev`, `npm run deploy:dev`, etc.
- Build process: Automatically runs `build:lambdas` and `build:website`
- Docker required for Lambda bundling
- Manual DNS configuration in Squarespace

## Key Patterns

### Repository Pattern
- Abstract data access with type-safe interfaces
- Return Pydantic models, not dicts
- See `docs/repositories.md` for responsibilities

### Service Pattern
- Business logic orchestration
- Coordinate multiple repositories
- Transform domain models to API responses

### Handler Pattern
- API Gateway integration
- Extract user context from authorizer
- Call service layer, format responses

See `docs/backend-code.md` for detailed patterns.
