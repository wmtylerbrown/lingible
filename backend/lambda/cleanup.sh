#!/bin/bash

# Lambda Functions Cleanup Script
# Cleans Python artifacts and cache files from the lambda directory

set -e

echo "🧹 Cleaning Lambda directory..."

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Function to safely remove files/directories
safe_remove() {
    local pattern="$1"
    local description="$2"

    if [ -n "$(find . -name "$pattern" 2>/dev/null | head -1)" ]; then
        print_status "Removing $description..."
        find . -name "$pattern" -delete 2>/dev/null || true
        print_success "Removed $description"
    else
        print_status "No $description found"
    fi
}

safe_remove_dir() {
    local pattern="$1"
    local description="$2"

    if [ -n "$(find . -name "$pattern" -type d 2>/dev/null | head -1)" ]; then
        print_status "Removing $description..."
        find . -name "$pattern" -type d -exec rm -rf {} + 2>/dev/null || true
        print_success "Removed $description"
    else
        print_status "No $description found"
    fi
}

# Python cache files
safe_remove "*.pyc" "Python compiled files"
safe_remove_dir "__pycache__" "Python cache directories"
safe_remove_dir ".pytest_cache" "Pytest cache directories"
safe_remove_dir ".mypy_cache" "MyPy cache directories"

# Coverage and test artifacts
safe_remove ".coverage" "Coverage files"
safe_remove_dir "htmlcov" "HTML coverage directories"

# System files
safe_remove ".DS_Store" "macOS system files"
safe_remove "Thumbs.db" "Windows system files"

# Build artifacts
safe_remove_dir "build" "Build directories"
safe_remove_dir "dist" "Distribution directories"
safe_remove_dir "*.egg-info" "Python egg info directories"

# Temporary files
safe_remove "*.log" "Log files"
safe_remove "*.tmp" "Temporary files"
safe_remove "*.swp" "Vim swap files"
safe_remove "*.swo" "Vim swap files"

echo ""
print_success "Lambda directory cleanup complete!"
print_status "Your Lambda code is now clean and ready for development"
echo ""
print_status "To run tests: python run_tests.py"
print_status "To install dependencies: pip install -r requirements.txt"
