#!/usr/bin/env bash
# Simple test runner - assumes you're already in a venv

set -e

echo "Running tests..."

# Check if in venv
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠ Warning: Not in a virtual environment"
    echo "Consider activating your venv first: source .venv/bin/activate"
    echo ""
fi

# Run pytest with options
pytest tests/ -v --tb=short "$@"

# For coverage
if [ "$1" == "--coverage" ]; then
    pytest tests/ --cov=doit --cov-report=term-missing --cov-report=html
fi