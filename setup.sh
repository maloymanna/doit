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
mkdir -p tests/unit
mkdir -p tests/integration
mkdir -p tests/fixtures

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

# Create test init files
touch tests/__init__.py
touch tests/unit/__init__.py
touch tests/integration/__init__.py

# Create pytest configuration
cat > pytest.ini << EOF
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --strict-markers --tb=short
markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
EOF

# Check the OS (Linux or Windows)
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux/Ubuntu
    PYTHON_BIN="python3"
    VENV_ACTIVATE=".venv/bin/activate"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    # Windows (Git Bash)
    PYTHON_BIN="python"
    VENV_ACTIVATE=".venv/Scripts/activate"
else
    echo "❌ Unsupported OS."
    exit 1
fi

echo "Using Python interpreter: $PYTHON_BIN"

# ------------------------------------------------------------
# 3. Create venv INSIDE project root (not nested)
# ------------------------------------------------------------
echo "🐍 Creating or updating virtual environment..."

if [ ! -d ".venv" ]; then
    "$PYTHON_BIN" -m venv .venv
    echo "✨ Created .venv in project root"
else
    echo "ℹ️  .venv already exists — reusing"
fi

# ------------------------------------------------------------
# 4. Activate venv
# ------------------------------------------------------------
echo "🔧 Activating virtual environment..."

if [ -f "$VENV_ACTIVATE" ]; then
    source "$VENV_ACTIVATE"
else
    echo "❌ Could not find venv activation script at: $VENV_ACTIVATE"
    exit 1
fi

# ------------------------------------------------------------
# 5. Install dependencies
# ------------------------------------------------------------
echo "⬆️ Upgrading pip + setuptools..."
$PYTHON_BIN -m pip install --upgrade pip setuptools wheel

echo "📥 Installing doit with development dependencies..."
$PYTHON_BIN -m pip install -e ".[dev,test]"

# ------------------------------------------------------------
# 6. Install Playwright browsers (if needed)
# ------------------------------------------------------------
echo "🌐 Installing Playwright browsers..."
playwright install msedge
playwright install chromium  # fallback

# ------------------------------------------------------------
# 7. Create sample workspace if not exists
# ------------------------------------------------------------
WORKSPACE_DIR="$HOME/app-workspace"
if [ ! -d "$WORKSPACE_DIR" ]; then
    echo "📁 Creating sample workspace at $WORKSPACE_DIR"
    mkdir -p "$WORKSPACE_DIR/.doit"
    mkdir -p "$WORKSPACE_DIR/projects"
    mkdir -p "$WORKSPACE_DIR/readonly_input"
    
    # Create default configs
    cat > "$WORKSPACE_DIR/.doit/config.yaml" << 'EOF'
# Doit Core Configuration
autonomy:
  mode: 0
  global_max_iterations: 10
  require_approval_for:
    - delete
    - git_push
    - git_reset_hard

browser:
  default_model: "GPT-5.1"
  completion_timeout_ms: 120000
  retry_attempts: 3
  screenshot_on_error: true

logging:
  level: "INFO"
  format: "json"
EOF

    cat > "$WORKSPACE_DIR/.doit/playwright_config.yaml" << 'EOF'
browser:
  channel: "msedge"
  headless: false
  slow_mo: 100
  viewport:
    width: 1280
    height: 900
  timeout_ms: 20000

selectors:
  new_chat_button: "button.new-chat"
  model_selector_button: "button.model-selector"
  send_enabled: "button.send:not([disabled])"
  prompt_input: "[contenteditable='true']"
  message_container: ".assistant-message"
EOF

    cat > "$WORKSPACE_DIR/.doit/allowlist.txt" << 'EOF'
# Allowed URLs for browser automation
https://usegpt.myorg
https://github.com/*
https://www.youtube.com/*
EOF

    echo "✓ Sample workspace created"
else
    echo "ℹ️  Workspace already exists at $WORKSPACE_DIR"
fi

# ------------------------------------------------------------
# 8. Run initial tests (optional)
# ------------------------------------------------------------
echo ""
echo "🎉 Setup complete!"
echo ""
echo "To start working:"
echo "  source $VENV_ACTIVATE"
echo ""
echo "To run tests:"
echo "  pytest                           # Run all tests"
echo "  pytest tests/unit/               # Run unit tests only"
echo "  pytest tests/unit/test_config.py # Run specific test"
echo ""
echo "To verify browser:"
echo "  cd examples"
echo "  python test_m2_chat_flow.py"
echo ""
echo "To use doit CLI:"
echo "  doit --help"