# Database Initialization

This document describes how to initialize and seed the Lingible database with required data.

## Overview

The Lingible backend requires two types of initial data:

1. **Lexicon Terms**: Canonical slang terms from `default_lexicon.json`
2. **Quiz Wrong Answer Pools**: Curated wrong answer options for each quiz category

Both are stored in the `LexiconTable` but serve different purposes and are initialized separately.

## Initialization Scripts

### Scripts Location

All initialization scripts are located in `backend/lambda/src/scripts/`:

- `init_lexicon.py` - Imports lexicon terms from JSON
- `init_quiz_pools.py` - Seeds wrong answer pools for quiz categories

### Prerequisites

**Environment Setup**:
```bash
cd backend/lambda
source ../../.venv/bin/activate
```

**Required Environment Variables**:
- `ENVIRONMENT`: Deployment environment (`dev` or `prod`)
- `LEXICON_TABLE`: DynamoDB table name (auto-detected from `ENVIRONMENT` if not set)
- `LOG_LEVEL`: Logging level (default: `INFO`)
- `ENABLE_TRACING`: Enable tracing (default: `false`)

**AWS Credentials**: Must be configured for the target environment.

## Lexicon Initialization

### Purpose

Imports canonical slang terms from `backend/lambda/src/data/lexicons/default_lexicon.json` into the `LexiconTable`. These terms are the authoritative source for slang definitions used in translations and quizzes.

### Source File

**Location**: `backend/lambda/src/data/lexicons/default_lexicon.json`

**Format**: JSON file with structure:
```json
{
  "version": "2.3",
  "generated_at": "2025-11-01",
  "count": 409,
  "items": [
    {
      "term": "cap",
      "variants": ["cap"],
      "pos": "expression",
      "gloss": "a lie;false",
      "examples": ["That's cap; he wasn't there."],
      "confidence": 0.9,
      "momentum": 1.0,
      "categories": ["slang"],
      "first_attested": "2018-01-01",
      ...
    }
  ]
}
```

### Running the Script

```bash
cd backend/lambda
source ../../.venv/bin/activate
ENVIRONMENT=dev LOG_LEVEL=INFO ENABLE_TRACING=false LEXICON_TABLE=lingible-lexicon-dev PYTHONPATH=src python src/scripts/init_lexicon.py
```

### What It Does

1. **Loads JSON**: Reads `default_lexicon.json` from the data directory
2. **Converts to Models**: Creates `SlangTerm` model instances for each term
3. **Estimates Quiz Metadata**:
   - Calculates `quiz_difficulty` based on confidence and momentum
   - Maps categories to `QuizCategory` enum
   - Sets `is_quiz_eligible=True` for all terms
4. **Saves to Database**: Uses `LexiconRepository.save_lexicon_term()` to persist each term
5. **Logs Progress**: Reports every 50 terms and final summary

### Expected Output

```
Starting lexicon initialization...
Imported: 409 terms
Failed: 0 terms
All terms imported successfully!
```

### Verification

```bash
# Count terms in table
aws dynamodb scan --table-name lingible-lexicon-dev \
  --filter-expression "begins_with(PK, :prefix)" \
  --expression-attribute-values '{":prefix":{"S":"TERM#"}}' \
  --select COUNT \
  --region us-east-1
```

## Quiz Pools Initialization

### Purpose

Creates wrong answer pools for each quiz category. These pools provide plausible but incorrect answer options for multiple-choice quiz questions.

### Running the Script

```bash
cd backend/lambda
source ../../.venv/bin/activate
ENVIRONMENT=dev LOG_LEVEL=INFO ENABLE_TRACING=false LEXICON_TABLE=lingible-lexicon-dev PYTHONPATH=src python src/scripts/init_quiz_pools.py
```

### What It Does

1. **Loads Lexicon**: Validates pool items against actual lexicon meanings
2. **Removes Conflicts**: Automatically removes pool items that match real term meanings
3. **Creates Pools**: Stores 9 category pools (50-100 options each) in `LexiconTable`
4. **Storage Format**: `PK=QUIZPOOL#{category}`, `SK=CATEGORY#{category}`

### Categories

- `approval` - Positive approval terms
- `disapproval` - Negative/disapproval terms
- `emotion` - Emotional expressions
- `food` - Food-related slang
- `appearance` - Appearance/style terms
- `social` - Social interaction terms
- `authenticity` - Authenticity/realness terms
- `intensity` - Intensity/exaggeration terms
- `general` - General purpose terms

### Expected Output

```
Wrong answer pool seeding completed
Pools created: 9
Pools failed: 0
Validation warnings: 36 (items removed that matched lexicon)
```

### Verification

```bash
# Count pools
aws dynamodb scan --table-name lingible-lexicon-dev \
  --filter-expression "begins_with(PK, :prefix)" \
  --expression-attribute-values '{":prefix":{"S":"QUIZPOOL#"}}' \
  --select COUNT \
  --region us-east-1

# List pool sizes
aws dynamodb scan --table-name lingible-lexicon-dev \
  --filter-expression "begins_with(PK, :prefix)" \
  --expression-attribute-values '{":prefix":{"S":"QUIZPOOL#"}}' \
  --query 'Items[*].{Category:category.S,PoolSize:pool_size.N}' \
  --output table \
  --region us-east-1
```

## Initialization Workflow

### For New Environment

**Complete initialization order**:

1. **Deploy Infrastructure**: Ensure DynamoDB tables exist (via CDK)
2. **Initialize Lexicon**: Run `init_lexicon.py` to import terms
3. **Initialize Quiz Pools**: Run `init_quiz_pools.py` to seed wrong answer pools

**Quick Command**:
```bash
# Initialize everything
cd backend/lambda
source ../../.venv/bin/activate
export ENVIRONMENT=dev
export LOG_LEVEL=INFO
export ENABLE_TRACING=false
export LEXICON_TABLE=lingible-lexicon-dev
export PYTHONPATH=src

python src/scripts/init_lexicon.py
python src/scripts/init_quiz_pools.py
```

### For Updates

**Lexicon Updates**:
- Update `default_lexicon.json` with new terms
- Re-run `init_lexicon.py` (will overwrite existing terms with same PK/SK)
- Note: Script is idempotent - safe to run multiple times

**Quiz Pool Updates**:
- Update pool definitions in `init_quiz_pools.py` (edit `WRONG_ANSWER_POOLS` dict)
- Re-run `init_quiz_pools.py` (will overwrite existing pools)
- Note: Script validates against current lexicon before seeding

## Data Sources

### default_lexicon.json

**Location**: `backend/lambda/src/data/lexicons/default_lexicon.json`

**Maintenance**:
- Curated list of canonical slang terms
- Updated periodically with new terms
- Version tracked in JSON metadata (`version`, `generated_at`)
- Current version: 2.3 (409 terms)

**Schema**:
- Each term includes: `term`, `gloss`, `examples`, `confidence`, `momentum`, `categories`, `first_attested`
- Used for translation lookups and quiz question generation
- Terms are marked as `is_quiz_eligible=True` during import

### Wrong Answer Pools

**Location**: Hardcoded in `init_quiz_pools.py` (`WRONG_ANSWER_POOLS` dictionary)

**Maintenance**:
- Curated lists of plausible wrong answers per category
- 50-100 options per category
- Automatically validated against lexicon to prevent conflicts
- Updated by editing the script and re-running

## Troubleshooting

### Import Failures

**Problem**: Terms fail to import with validation errors
**Solution**: Check JSON format, ensure `gloss` fields are strings (not booleans)

### Pool Validation Warnings

**Problem**: Many pool items removed during validation
**Solution**: Normal behavior - script removes items that match actual term meanings to prevent correct answers in wrong answer pools

### Missing Environment Variables

**Problem**: `ConfigurationError: Required environment variable 'LEXICON_TABLE' not found`
**Solution**: Set `LEXICON_TABLE` explicitly or ensure `ENVIRONMENT` is set correctly

### AWS Credentials

**Problem**: `NoCredentialsError` or permission denied
**Solution**: Configure AWS credentials for target environment (`aws configure` or environment variables)

## Related Documentation

- [Database Schema](database-schema.md) - Complete table schemas and indexes
- [Repositories](repositories.md) - Repository layer and data access patterns
- [Development Guide](development.md) - Development environment setup
