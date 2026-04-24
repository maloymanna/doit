#!/usr/bin/env bash
set -e

PROJECT_NAME="doit"

# ------------------------------------------------------------
# 1. Ensure we are in the correct project root
# ------------------------------------------------------------
CURRENT_DIR_NAME=$(basename "$PWD")

if [ "$CURRENT_DIR_NAME" != "$PROJECT_NAME" ]; then
    echo "❌ ERROR: setup.sh must be run from the project root directory: $PROJECT_NAME/"
    echo "You are currently in: $CURRENT_DIR_NAME/"
    exit 1
fi

echo "📁 Running setup inside project root: $PWD"

# ------------------------------------------------------------
# 2. Ensure src/ directory structure exists
# ------------------------------------------------------------
echo "📦 Ensuring src layout exists..."
mkdir -p src/doit/browser
mkdir -p src/doit/plugins
mkdir -p examples

touch src/doit/__init__.py
touch src/doit/cli.py
touch src/doit/orchestrator.py
touch src/doit/config.py
touch src/doit/permissions.py
touch src/doit/files.py
touch src/doit/logging.py
touch src/doit/git_wrapper.py
touch src/doit/browser/__init__.py
touch src/doit/browser/controller.py
touch src/doit/plugins/__init__.py
touch src/doit/plugins/base.py

# ------------------------------------------------------------
# 3. Create venv INSIDE project root (not nested)
# ------------------------------------------------------------
echo "🐍 Creating or updating virtual environment..."

if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo "✨ Created .venv in project root"
else
    echo "ℹ️  .venv already exists — reusing"
fi

# ------------------------------------------------------------
# 4. Activate venv
# ------------------------------------------------------------
echo "🔧 Activating virtual environment..."

if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
elif [ -f ".venv/Scripts/activate" ]; then
    source .venv/Scripts/activate
else
    echo "❌ Could not find venv activation script."
    exit 1
fi

# ------------------------------------------------------------
# 5. Install dependencies
# ------------------------------------------------------------
echo "⬆️ Upgrading pip + setuptools..."
pip install --upgrade pip setuptools wheel

echo "📥 Installing doit in editable mode..."
pip install -e .

echo "🎉 Setup complete!"
echo
echo "To start working, run:"
echo "  source .venv/bin/activate"
