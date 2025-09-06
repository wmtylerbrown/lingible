# Poetry Migration for Backend Dependencies

## Overview

We've migrated from duplicate `requirements.txt` files to Poetry for better dependency management. This provides:

- ✅ **Single source of truth** for all dependencies
- ✅ **Separate runtime vs development dependencies**
- ✅ **Lock file for reproducible builds**
- ✅ **Better dependency resolution**
- ✅ **Cleaner build process**

## Migration Changes

### Files Added
- `backend/lambda/pyproject.toml` - Poetry configuration with runtime and dev dependencies
- `backend/lambda/setup-poetry.sh` - Setup script for Poetry initialization
- `backend/lambda/poetry.lock` - Generated lock file (after running setup)

### Files Modified
- `backend/infrastructure/scripts/build-dependencies-lambda.sh` - Updated to use Poetry export

### Files to Remove (after testing)
- `backend/lambda/requirements.txt` - Replaced by pyproject.toml
- `backend/infrastructure/lambda-layer-requirements.txt` - Replaced by Poetry export

## Setup Instructions

### 1. Install Poetry (if not already installed)
```bash
curl -sSL https://install.python-poetry.org | python3 -
# or
pip install poetry
```

### 2. Initialize Poetry in the backend
```bash
cd backend/lambda
./setup-poetry.sh
```

### 3. Activate Poetry environment
```bash
poetry shell
```

## Dependency Management

### Adding Runtime Dependencies
```bash
poetry add boto3
poetry add "pydantic>=2.11.7"
```

### Adding Development Dependencies
```bash
poetry add --group dev pytest
poetry add --group dev black
```

### Removing Dependencies
```bash
poetry remove package-name
```

### Viewing Dependencies
```bash
poetry show                    # All packages
poetry show --only=main        # Runtime only
poetry show --only=dev         # Dev only
```

## Build Process

The Lambda build process now:

1. Uses `poetry export` to generate a clean requirements.txt with only runtime dependencies
2. CDK uses Docker bundling to install packages with Lambda-specific platform flags
3. No manual layer creation needed - CDK handles everything in Docker

## Benefits

### Before (Problems)
- ❌ Duplicate requirements files
- ❌ Manual sync between files
- ❌ Dev dependencies mixed with runtime
- ❌ No lock file for reproducible builds

### After (Solutions)
- ✅ Single pyproject.toml source of truth
- ✅ Automatic dependency resolution
- ✅ Clean separation of runtime vs dev
- ✅ poetry.lock for reproducible builds
- ✅ Better version conflict resolution

## Testing the Migration

1. **Setup Poetry**: `cd backend/lambda && ./setup-poetry.sh`
2. **Test Development**: `poetry run pytest`
3. **Generate Requirements**: `cd ../infrastructure && ./scripts/build-dependencies-lambda.sh`
4. **Verify Requirements**: Check that `backend/lambda/requirements.txt` contains runtime dependencies
5. **Deploy with CDK**: CDK will use Docker to build Lambda layers from requirements.txt

## Rollback Plan

If issues arise, we can quickly rollback by:
1. Restoring the original `build-dependencies-lambda.sh`
2. Keeping the old requirements files
3. The Poetry files are additive and don't break existing functionality
