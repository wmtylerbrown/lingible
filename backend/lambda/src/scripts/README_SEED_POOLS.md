# Wrong Answer Pool Seeding

## Purpose

Populates DynamoDB with wrong answer pools for quiz categories, replacing the old per-term storage approach.

## Benefits

- **99% Storage Reduction**: 9 pool records vs ~1,500 term fields
- **Better Variety**: 50-100 options per category vs 3 per term
- **Faster Performance**: O(1) lookup vs O(20) queries
- **Simpler Logic**: Always use pools (no fallback needed)

## Usage

```bash
cd backend/lambda
source ../../.venv/bin/activate
ENVIRONMENT=dev PYTHONPATH=src python src/scripts/seed_wrong_answer_pools.py
```

## Environment Variables

- `ENVIRONMENT`: Deployment environment (dev/prod)
- `TERMS_TABLE`: DynamoDB table name (auto-detected from ENVIRONMENT if not set)

## What It Does

Creates 9 DynamoDB records (one per quiz category):
- `PK: QUIZPOOL#{category}`
- `SK: CATEGORY#{category}`
- `pool: [50-100 curated wrong answer strings]`

Categories:
- approval
- disapproval
- emotion
- food
- appearance
- social
- authenticity
- intensity
- general

## After Seeding

1. Wrong answer pools are loaded at Lambda cold start
2. QuizService caches pools in-memory (class-level cache)
3. Each question randomly selects 3 options from the category pool
4. Fallback to dynamic generation if pool unavailable
