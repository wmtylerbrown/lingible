# Database Schema

This document defines the current DynamoDB table schemas, primary keys, indexes, and access patterns for the Lingible backend.

## Table Overview

| Table | Primary Key | Purpose | TTL | PITR |
| --- | --- | --- | --- | --- |
| `SubmissionsTable` | `PK=TERM#{slug}`, `SK=SUBMISSION#{id}` | User slang submissions and moderation | Optional | Yes |
| `LexiconTable` | `PK=TERM#{slug}`, `SK=METADATA#lexicon` | Canonical lexicon entries | None | Yes |
| `TrendingTable` | `PK=TERM#{slug}`, `SK=METADATA#trending` | Trending analytics | 90 days | Yes |
| `UsersTable` | `PK=USER#{user_id}`, `SK` varies | User profiles, usage, quiz sessions | Per-item | Yes |
| `TranslationsTable` | `PK=USER#{user_id}`, `SK=TRANSLATION#{id}` | Translation history | Per-item | Yes |

## SubmissionsTable

**Primary Key**: `PK=TERM#{slug}`, `SK=SUBMISSION#{submission_id}`

**Attributes**:
- `submission_id` (string, unique)
- `user_id`, `slang_term`
- `meaning`, `example_usage`, `context`
- `status` (`pending`, `validated`, `auto_approved`, `admin_rejected`, etc.)
- `created_at`, `reviewed_at`
- `approval_type`, `reviewed_by`
- `llm_validation_status`, `llm_validation_result`
- `upvotes`, `upvoted_by`
- `ttl` (optional, for auto-expiration)

**Global Secondary Indexes**:

| Index | Key Schema | Projection | Purpose |
| --- | --- | --- | --- |
| `SubmissionsStatusIndex` | `PK=status`, `SK=created_at` | `INCLUDE` (`submission_id`, `user_id`, `slang_term`, `context`) | Moderation queues and voting flows |
| `SubmissionsByUserIndex` | `PK=user_id`, `SK=created_at` | `KEYS_ONLY` | User submission history |
| `SubmissionsByIdIndex` | `PK=submission_id` | `ALL` | Direct lookup by submission ID |
| `ValidationStatusIndex` | `PK=llm_validation_status` | `INCLUDE` (`submission_id`, `user_id`, `slang_term`) | Async validation processor |

**Consumers**: `SubmissionsRepository`, `SlangSubmissionService`, async validation handler, admin APIs

## LexiconTable

**Primary Key**: `PK=TERM#{slug}`, `SK=METADATA#lexicon`

**Attributes**:
- Core definition: `gloss`, `variants`, `examples`, `tags`, `regions`, `sources`
- Attestation: `first_attested`, `attestation_note`
- Quiz metadata: `is_quiz_eligible`, `quiz_difficulty`, `quiz_category`, `quiz_score`
- Observability: `confidence`, `momentum`, `last_updated`

**Global Secondary Indexes**:

| Index | Key Schema | Projection | Purpose |
| --- | --- | --- | --- |
| `LexiconSourceIndex` | `PK=source`, `SK=term` | `KEYS_ONLY` | Bulk exports and import verification |
| `LexiconQuizDifficultyIndex` | `PK=quiz_difficulty`, `SK=quiz_score` | `INCLUDE` (`term`, `gloss`, `examples`, `tags`) | Quiz generation by difficulty |
| `LexiconQuizCategoryIndex` | `PK=quiz_category`, `SK=quiz_score` | `INCLUDE` (`term`, `gloss`, `examples`, `tags`) | Category-specific quizzes |

**Consumers**: `LexiconRepository`, `QuizService`, export lexicon async job, translation service

## TrendingTable

**Primary Key**: `PK=TERM#{slug}`, `SK=METADATA#trending`

**Attributes**:
- `term`, `definition`, `category`
- `popularity_score`, `search_count`, `translation_count`
- `first_seen`, `last_updated`
- `is_active`, `example_usage`, `origin`, `related_terms`
- `ttl` (90-day expiration)

**Global Secondary Indexes**:

| Index | Key Schema | Projection | Purpose |
| --- | --- | --- | --- |
| `TrendingActiveIndex` | `PK=is_active`, `SK=popularity_score` | `INCLUDE` (`term`, `category`, `definition`) | Global top-N trending lists |
| `TrendingCategoryIndex` | `PK=category`, `SK=popularity_score` | `INCLUDE` (`term`, `definition`, `is_active`) | Category-specific trending queries |

**Consumers**: `TrendingRepository`, `TrendingService`, trending job async lambda

## UsersTable

**Primary Key**: `PK=USER#{user_id}`, `SK` varies by item type

**SK Patterns**:
- `PROFILE` - User profile data
- `USAGE#LIMITS` - Usage limit tracking
- `QUIZ_DAILY#YYYY-MM-DD` - Daily quiz statistics
- `QUIZ_SESSION#{session_id}` - Active quiz sessions

**Attributes**:
- Profile: `email`, `tier`, `status`, `created_at`, `updated_at`
- Usage: `daily_used`, `reset_daily_at`, `tier`
- Quiz: `quiz_count`, `session_status`, `total_score`, `total_possible`
- `ttl` (per-item, for quiz sessions and temporary data)

**Global Secondary Indexes**:

| Index | Key Schema | Projection | Purpose |
| --- | --- | --- | --- |
| `UsersTierIndex` | `PK=tier`, `SK=updated_at` | `KEYS_ONLY` | Admin reports by subscription tier (optional) |

**Consumers**: `UserRepository`, `UserService`, `QuizService`, account management

## TranslationsTable

**Primary Key**: `PK=USER#{user_id}`, `SK=TRANSLATION#{translation_id}`

**Attributes**:
- `translation_id`, `original_text`, `translated_text`
- `direction`, `confidence_score`, `model_used`
- `created_at`
- `ttl` (optional, per-item)

**Global Secondary Indexes**: None currently

**Future Index** (optional):
- `TranslationsByCreatedAtIndex`: `PK=model_used`, `SK=created_at` for cross-user analytics

**Consumers**: `TranslationRepository`, `TranslationService`, translation history APIs

## Access Patterns

### SubmissionsRepository
- Query by status: `SubmissionsStatusIndex` (`status`, `created_at`)
- Query by user: `SubmissionsByUserIndex` (`user_id`, `created_at`)
- Get by ID: `SubmissionsByIdIndex` (`submission_id`)
- Query validation status: `ValidationStatusIndex` (`llm_validation_status`)

### LexiconRepository
- Export by source: `LexiconSourceIndex` (`source`, `term`)
- Quiz by difficulty: `LexiconQuizDifficultyIndex` (`quiz_difficulty`, `quiz_score`)
- Quiz by category: `LexiconQuizCategoryIndex` (`quiz_category`, `quiz_score`)
- Get by term: Primary key lookup (`TERM#{slug}`, `METADATA#lexicon`)

### TrendingRepository
- Global trending: `TrendingActiveIndex` (`is_active`, `popularity_score` DESC)
- Category trending: `TrendingCategoryIndex` (`category`, `popularity_score` DESC)

### UserRepository
- Get user profile: Primary key (`USER#{user_id}`, `PROFILE`)
- Get usage limits: Primary key (`USER#{user_id}`, `USAGE#LIMITS`)
- Get quiz session: Primary key (`USER#{user_id}`, `QUIZ_SESSION#{id}`)
- Query by tier: `UsersTierIndex` (`tier`, `updated_at`) - if implemented

### TranslationRepository
- Get user translations: Primary key query (`USER#{user_id}`, `SK` begins with `TRANSLATION#`)
- Get single translation: Primary key (`USER#{user_id}`, `TRANSLATION#{id}`)

## Index Naming Conventions

- Use descriptive names: `<Table><Purpose>Index` (e.g., `SubmissionsStatusIndex`)
- Avoid numeric suffixes (e.g., `GSI1`, `GSI2`) except when DynamoDB requires uniqueness
- Keep projections tight: `KEYS_ONLY` or `INCLUDE` unless `ALL` is necessary

## Configuration

**Environment Variables**: Each repository reads table names from environment:
- `USERS_TABLE`
- `TRANSLATIONS_TABLE`
- `SUBMISSIONS_TABLE`
- `LEXICON_TABLE`
- `TRENDING_TABLE`

**CDK Configuration**: Table names defined in `shared/config/infrastructure/{env}.json`

## Data Protection

- **Encryption**: All tables use server-side encryption (SSE) at rest
- **Point-in-Time Recovery**: Enabled on all tables (35-day recovery window)
- **TTL**: Automatic cleanup for trending data (90 days) and temporary items

## Database Initialization

The LexiconTable requires initial data to be populated before the system can function:

1. **Lexicon Terms**: Imported from `backend/lambda/src/data/lexicons/default_lexicon.json`
2. **Quiz Wrong Answer Pools**: Curated pools for each quiz category

See [Database Initialization](database-initialization.md) for complete setup instructions.
