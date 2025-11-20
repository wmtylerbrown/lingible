# Repository Responsibilities

This document maps each DynamoDB table to its owning repository module(s) and describes access patterns and responsibilities. All repository tests belong in `backend/lambda/tests_v2/`.

## Submissions Domain

- **Repository**: `src/repositories/submissions_repository.py`
- **Table**: `SubmissionsTable`
- **Primary Keys**: `PK=TERM#{slang}`, `SK=SUBMISSION#{submission_id}`
- **Access Patterns**:
  - Create/read/update user submissions
  - Query moderation queues via `SubmissionsStatusIndex` (`status`, `status_created_at`)
  - Fetch submissions by user via `SubmissionsByUserIndex` (`user_id`, `user_created_at`)
  - Direct lookup via `SubmissionsByIdIndex` (`submission_id`)
  - Query validation status via `ValidationStatusIndex` (`llm_validation_status`)
- **Responsibilities**:
  - Create/update submissions, validation writes, admin approval, deduping
  - Used by `SlangSubmissionService`, async validation handler, admin APIs, upvote endpoints
- **Notes**: Dedicated table enables tight TTL (optional) and removes write amplification from lexicon/trending workflows.
- **Tests**: `tests_v2/test_submissions_repository.py` covering CRUD + index-based queries.

## Lexicon & Quiz Domain

- **Repository**: `src/repositories/lexicon_repository.py`
- **Table**: `LexiconTable`
- **Primary Keys**: `PK=TERM#{slang}`, `SK=METADATA#lexicon`
- **Access Patterns**:
  - Canonical CRUD operations
  - Quiz term retrieval via `LexiconQuizDifficultyIndex` (`quiz_difficulty`, `quiz_score`)
  - Category-specific quizzes via `LexiconQuizCategoryIndex` (`quiz_category`, `quiz_score`)
  - Export/import verification via `LexiconSourceIndex` (`source`, `term`)
- **Responsibilities**:
  - Manage canonical lexicon entries (import/export)
  - Provide quiz-ready terms filtered by difficulty/category
  - Maintain attestation metadata and quiz statistics
  - Used by `QuizService`, export lexicon async job, migration scripts
- **Notes**: Canonical data no longer competes with submissions; quiz metadata lives alongside lexicon entries with right-sized projections.
- **Tests**: `tests_v2/test_lexicon_repository.py` validating lexicon CRUD and quiz index usage.

## Trending Domain

- **Repository**: `src/repositories/trending_repository.py`
- **Table**: `TrendingTable`
- **Primary Keys**: `PK=TERM#{slang}`, `SK=METADATA#trending`
- **Access Patterns**:
  - Global top-N queries via `TrendingActiveIndex` (`is_active`, `popularity_score`)
  - Category-specific leaderboards via `TrendingCategoryIndex` (`category`, `popularity_score`)
- **Responsibilities**:
  - Create/update trending term snapshots
  - Query top terms globally and per category
  - Increment counters (search/translation counts) with consistent TTL behavior
  - Used by `TrendingJob` async lambda + `trending_api`
- **Notes**: TTL (90 days) keeps dataset lean and isolated from lexicon/submission churn.
- **Tests**: `tests_v2/test_trending_repository.py` updated to target the new table fixture.

## Users Domain

- **Repository**: `src/repositories/user_repository.py`
- **Table**: `UsersTable`
- **Primary Keys**: `PK=USER#{user_id}`, `SK` varies (`PROFILE`, `USAGE#LIMITS`, `QUIZ_DAILY#<date>`, quiz session IDs, etc.)
- **Access Patterns**:
  - Get/create/update/delete profile records, usage limits, quiz stats
  - All operations are strict per-user PK lookups (no GSIs currently)
  - `QuizService` stores quiz session records under `SK=QUIZ_SESSION#...`
- **Responsibilities**:
  - Profile management, usage counters, quiz stats
  - Optional future usage of `UsersTierIndex` for tier-based queries
- **Limitations**: No way to list/filter users by tier, email, status without scans (future GSI may address this)
- **Tests**: `tests_v2/test_user_repository.py` covers CRUD operations. Expand to cover tier-index queries if/when the index is added.

## Translations Domain

- **Repository**: `src/repositories/translation_repository.py`
- **Table**: `TranslationsTable`
- **Primary Keys**: `PK=USER#{user_id}`, `SK=TRANSLATION#{translation_id}`
- **Access Patterns**:
  - Per-user history queries (`get_user_translations`)
  - Create/delete translations, get a single translation
  - No GSIs currently; all operations are per-user PK lookups
- **Responsibilities**:
  - Per-user history storage
  - Potential future analytics index for global reporting (e.g., latest translations, per-model stats)
- **Limitations**: No GSIs for global reporting without scans (future GSI may address this)
- **Tests**: `tests_v2/test_translation_repository.py` covers CRUD and pagination.

## Shared Utilities / Services

- Ensure services (`SlangSubmissionService`, `TrendingService`, `QuizService`, etc.) depend on the new repositories instead of touching DynamoDB directly.
- Update dependency injection to accept the new repository classes, enabling targeted unit tests.

## Documentation & Constants

- Define table/index names in a single module (`src/config/dynamodb_resources.py`) so CDK, repositories, and tests share identical identifiers.
- Update README/API docs under `docs/` whenever repository responsibilities change.
