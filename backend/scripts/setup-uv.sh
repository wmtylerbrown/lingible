#!/bin/bash

set -e

echo "🚀 Setting up uv for Lingible backend..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ uv is not installed. Please install it first:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo "   or: brew install uv"
    exit 1
fi

# AGENTS.md's convention is one venv at the repo root (never a nested backend/lambda/.venv).
# UV_PROJECT_ENVIRONMENT tells `uv sync` to manage that venv instead of its own project-relative
# default.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
export UV_PROJECT_ENVIRONMENT="$ROOT/.venv"

echo "📦 Installing dependencies and generating lock file..."
(cd "$ROOT/backend/lambda" && uv sync --all-extras)

echo "✅ uv setup complete!"
echo ""
echo "📋 Next steps:"
echo "   1. Run 'source .venv/bin/activate' (from the repo root) to activate the virtual environment"
echo "   2. Run 'nox -s test' (or '.venv/bin/pytest backend/lambda/tests') to run tests"
echo "   3. The build script will now use uv for Lambda layer creation"
echo ""
echo "🔧 Useful uv commands (from backend/lambda)"
echo "   uv add <package>                    # Add runtime dependency"
echo "   uv add --group dev <pkg>            # Add dev dependency"
echo "   uv add --optional <extra> <pkg>     # Add to a runtime extra (receipt-validation/slang-validation)"
echo "   uv remove <package>                 # Remove dependency"
echo "   uv tree                             # Show installed packages"
echo "   uv export --no-dev --format requirements-txt  # Export runtime requirements"
