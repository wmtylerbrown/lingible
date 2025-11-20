# Test Strategy (DynamoDB/CDK Refactor)

This document captures the testing approach for the DynamoDB redesign. All tests live under `backend/lambda/tests/`.

## Guiding Principles

- **Test-first for every code change**: repositories, services, and CDK stacks must have failing tests before refactors begin.
- **Unit-level scope**: continue to use `moto` + `tests/conftest.py` fixtures (`users_table`, `translations_table`, `submissions_table`, `lexicon_table`, `trending_table`) to avoid deploying real infrastructure.
- **One fixture per table layout**: every DynamoDB table has a dedicated fixture so tests provision only the indexes they need.
- **Index-aware coverage**: whenever we add/rename a GSI, write tests that exercise the specific query/update paths that depend on the index.
- **Coverage guardrails**: repositories stay ≥ 90% statement coverage, `translation`/`user`/`quiz` services stay ≥ 90%, and every other service stays ≥ 50% (push higher when practical).

## Current Coverage Snapshot

| File | Focus | Notes |
| --- | --- | --- |
| `test_user_repository.py` | CRUD + usage counters on Users table | Uses `users_table` fixture; no GSI coverage today. |
| `test_translation_repository.py` | Per-user translation history | Strictly PK/SK queries; highlights lack of cross-user access tests. |
| `test_submissions_repository.py` | Submission + validation workflow | Uses `submissions_table` fixture with status/user/id/validation GSIs. |
| `test_lexicon_repository.py` | Canonical lexicon + quiz metadata | Uses `lexicon_table` fixture with quiz difficulty/category indexes. |
| `test_trending_repository.py` | Trending analytics | Uses `trending_table` fixture (active + category indexes). |
| `test_quiz_service.py` | Quiz workflows | Patches `LexiconRepository`/`UserRepository`; focuses on service logic. |
| `test_subscription_repository.py` / `test_translation_service.py` | Non-DynamoDB mocks | Out of scope for short-term table changes. |

### Latest Coverage Metrics (2025-11-15)

- **Repositories**: Submissions 94%, Lexicon 97%, Trending 99%, Translation 100%, User 90%, Subscription 100%.
- **Priority Services**: Translation 91%, User 92%, Quiz 91% (all ≥ 90%).
- **Other Services**: Slang Lexicon 95%, Slang LLM 86%, Slang Matching 94%, Slang Service 91%, Slang Submission 80%, Slang Validation 93%, Apple StoreKit 84%, Subscription Service 73%, Trending Service 56% (meets ≥ 50%, earmarked for future uplift).
- Run `ENVIRONMENT=test PYTHONPATH=src python-m pytest tests --cov=src --cov-report=term-missing` (from `backend/lambda` directory) before merges to keep the table up to date.

## Test Coverage Needs Per Workstream

1. **Index Rationalization & Naming**
   - Add explicit tests for any repository/service that queries a trimmed projection to ensure only expected attributes are present.
   - Create negative tests verifying that attempting to access removed attributes (e.g., momentum from GSI2 projection) fails fast.
   - When reclaiming index names (e.g., `GSI3`, `GSI4`), document the new semantics in the test module docstrings.

2. **New Targeted GSIs (`submission_id`, `user_id`)**
   - Add repository tests that currently rely on scans (`get_submission_by_id`, `get_user_submissions`) to assert they hit the new GSI paths.
   - Use pytest markers to request the new GSIs on the `submissions_table` fixture (status/user/id/validation) instead of relying on scans.

3. **Table Segmentation**
   - Introduce dedicated fixtures for each new table (e.g., `submissions_table`, `lexicon_table`, `trending_table`) with schema definitions that match the CDK stacks.
   - Add regression tests that verify repositories cannot accidentally mix data across tables (e.g., `TrendingRepository` should only talk to the trending table).

4. **Repository Realignment**
   - For each new repository module, add a corresponding `tests/test_<repo>.py` with CRUD/path coverage mirroring the existing suites.
   - Where repositories share utilities (e.g., ID generation, TTL helpers), add unit tests for those helpers to avoid duplicating assertions in every repo test.

5. **CDK Verification**
   - Add snapshot/unit tests for CDK constructs (e.g., using `assertions.Template`) to verify table/GSIs definitions match the documented schema.
   - Ensure the tests assert index names, key schemas, and projection types so renames are caught early.

## Action Items

- [x] Extend `tests/conftest.py` with fixtures for the new CDK tables.
- [ ] Add pytest markers for new GSIs so repository tests can opt-in without affecting unrelated suites.
- [x] Create repository-specific test modules as soon as new repositories are introduced.
- [ ] Add a CDK-focused test suite (e.g., `tests/test_cdk_tables.py`) once the infrastructure definitions are ready.

This strategy will evolve as the table design solidifies; update this document whenever new behaviors or fixtures are introduced.
