#!/bin/bash

set -e

echo "🎭 Setting up Poetry for Lingible backend..."

# Check if we're in a virtual environment
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  Warning: No virtual environment detected!"
    echo "   It's recommended to run this from the project's .venv:"
    echo "   python3.13 -m venv .venv"
    echo "   source .venv/bin/activate"
    echo ""
fi

# Check if Poetry is installed
if ! command -v poetry &> /dev/null; then
    echo "❌ Poetry is not installed. Please install it first:"
    echo "   curl -sSL https://install.python-poetry.org | python3 -"
    echo "   or: pip install poetry"
    exit 1
fi

# Install dependencies and generate lock file
echo "📦 Installing dependencies and generating lock file..."
cd lambda
poetry install

echo "✅ Poetry setup complete!"
echo ""
echo "📋 Next steps:"
echo "   1. Run 'poetry shell' to activate the virtual environment"
echo "   2. Run 'poetry run pytest' to run tests"
echo "   3. The build script will now use Poetry for Lambda layer creation"
echo ""
echo "🔧 Useful Poetry commands:"
echo "   poetry add <package>           # Add runtime dependency"
echo "   poetry add --group dev <pkg>   # Add dev dependency"
echo "   poetry remove <package>        # Remove dependency"
echo "   poetry show                    # Show installed packages"
echo "   poetry export --without dev    # Export runtime requirements"
