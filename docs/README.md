# Lingible Documentation

This directory contains comprehensive documentation for the Lingible backend architecture, data structures, deployment, and development practices.

## Core Documentation

### Architecture & Design

- **[Architecture](architecture.md)** - System architecture, components, request flows, and design decisions
- **[Functions](functions.md)** - All Lambda functions and service classes with their purposes and responsibilities
- **[Backend Code](backend-code.md)** - Code structure, patterns, and organization principles

### Data & Database

- **[Database Schema](database-schema.md)** - Complete DynamoDB table schemas, indexes, and access patterns
- **[Database Initialization](database-initialization.md)** - How to initialize and seed the database with lexicon terms and quiz pools
- **[Repositories](repositories.md)** - Repository responsibilities, access patterns, and data access layer

### Deployment & Infrastructure

- **[Infrastructure](infrastructure.md)** - CDK stack architecture, deployment process, and infrastructure management
- **[Security](security.md)** - Security practices, secrets management, authentication, and authorization

### Development

- **[Development Guide](development.md)** - Development environment setup, testing strategies, and code quality standards
- **[Test Strategy](test-strategy.md)** - Testing approach, coverage targets, and TDD workflow

## Quick Reference

### For New Developers

1. Start with [Architecture](architecture.md) to understand the system
2. Read [Development Guide](development.md) for setup and workflows
3. Review [Backend Code](backend-code.md) for code patterns
4. Check [Functions](functions.md) to understand what each component does

### For Database Work

1. Review [Database Schema](database-schema.md) for complete table and index definitions
2. See [Repositories](repositories.md) for access patterns and responsibilities
3. Check [Database Initialization](database-initialization.md) for setting up initial data

### For Deployment

1. Read [Infrastructure](infrastructure.md) for deployment process
2. Review [Security](security.md) for secrets management
3. Follow deployment steps in infrastructure guide

## Document Maintenance

**Keep Documentation Updated**: When making changes to:
- **Architecture**: Update `architecture.md` and `functions.md`
- **Database**: Update `database-schema.md`, `repositories.md`, and `database-initialization.md`
- **Infrastructure**: Update `infrastructure.md`
- **Code Patterns**: Update `backend-code.md` and `development.md`

**Review Cadence**: Review and update documentation quarterly or when major changes occur.
