# Running the Lexicon Migration Script

## What This Script Does

The `migrate_lexicon.py` script imports all slang terms from `default_lexicon.json` into the DynamoDB `slang_terms` table. It:

1. **Loads the lexicon**: Reads `default_lexicon.json` (contains ~500 slang terms)
2. **Maps data**: Converts lexicon format to DynamoDB structure with all required fields
3. **Calculates difficulty**: Estimates quiz difficulty based on confidence and momentum scores
4. **Maps categories**: Converts lexicon categories to quiz categories
5. **Generates quiz options**: Creates plausible wrong answer options for quiz functionality
6. **Imports to DynamoDB**: Creates entries in the `slang_terms` table via `SlangTermRepository`

## Prerequisites

1. **Environment Variables** - The script needs these AWS/DynamoDB environment variables:
   - `ENVIRONMENT` - Set to `dev` or `prod` (determines which DynamoDB table)
   - `SLANG_TERMS_TABLE` - DynamoDB table name (e.g., `lingible-slang-submissions-dev`)
   - AWS credentials configured (via `~/.aws/credentials` or environment variables)

2. **Python Environment** - Use the project's virtual environment:
   ```bash
   source .venv/bin/activate
   ```

3. **Lexicon File** - Ensure `backend/lambda/src/data/lexicons/default_lexicon.json` exists

## How to Run

### Option 1: Run Directly (Recommended)

```bash
cd backend/lambda
source ../../.venv/bin/activate
export ENVIRONMENT=dev
export SLANG_TERMS_TABLE=lingible-slang-submissions-dev
export PYTHONPATH=src
python src/scripts/migrate_lexicon.py
```

### Option 2: Set All Required Environment Variables

Based on your infrastructure config, you need these variables:

```bash
cd backend/lambda
source ../../.venv/bin/activate

# Set environment (dev or prod)
export ENVIRONMENT=dev

# DynamoDB table name (matches your config)
export SLANG_TERMS_TABLE=lingible-slang-submissions-dev

# Set Python path
export PYTHONPATH=src

# Run the script
python src/scripts/migrate_lexicon.py
```

## What Gets Imported

Each lexicon term becomes a DynamoDB item with:
- **Primary Keys**: `PK=TERM#{term}`, `SK=SOURCE#lexicon#{term}`
- **Term data**: slang_term, meaning, examples, variants
- **Status**: Always "approved" (lexicon terms are pre-approved)
- **Quiz fields**: difficulty, category, wrong answer options
- **Lexicon metadata**: confidence, momentum, age_rating, categories
- **GSI fields**: For querying by status, quiz difficulty, category, source

## Expected Output

```
Starting lexicon migration...
Migration completed successfully!
Imported: 500 terms
Failed: 0 terms
All terms imported successfully!
```

## Troubleshooting

1. **"Table not found"** - Check `SLANG_TERMS_TABLE` matches your deployed table name
2. **"Access denied"** - Ensure AWS credentials have DynamoDB write permissions
3. **"Module not found"** - Set `PYTHONPATH=src` in backend/lambda directory
4. **"Lexicon file not found"** - Check `src/data/lexicons/default_lexicon.json` exists

## Safety

- The script uses `create_lexicon_term()` which should handle duplicates
- Each term gets a unique `PK/SK` combination
- If a term already exists, the repository should handle it gracefully
- The script logs progress every 50 terms
