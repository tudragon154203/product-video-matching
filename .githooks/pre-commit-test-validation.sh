#!/bin/bash
# Pre-commit hook for test validation
# This hook validates that tests can be imported and basic syntax is correct

set -e

echo "🔍 Running pre-commit test validation..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Check if we're in the right directory
if [ ! -f "pytest.ini" ]; then
    print_status $RED "❌ Error: pytest.ini not found. Please run from project root."
    exit 1
fi

# Check if test files are being modified
test_files_changed=$(git diff --cached --name-only | grep -E "^tests/.*\.py$" || true)

if [ -z "$test_files_changed" ]; then
    print_status $GREEN "✅ No test files changed. Skipping validation."
    exit 0
fi

print_status $YELLOW "📝 Test files modified: $test_files_changed"

# Validate Python syntax for changed test files
for file in $test_files_changed; do
    if [ -f "$file" ]; then
        print_status $YELLOW "🔍 Checking syntax: $file"
        
        # Check Python syntax
        if ! python -m py_compile "$file"; then
            print_status $RED "❌ Syntax error in $file"
            exit 1
        fi
        
        # Check for common issues
        if grep -q "import pytest" "$file"; then
            if ! grep -q "@pytest.mark" "$file"; then
                print_status $YELLOW "⚠️  Warning: $file uses pytest but has no markers"
            fi
        fi
    fi
done

# Validate pytest configuration
print_status $YELLOW "🔍 Validating pytest configuration..."
if ! python -c "import pytest; print('pytest configuration OK')" 2>/dev/null; then
    print_status $RED "❌ pytest configuration error"
    exit 1
fi

# Check if test collection works
print_status $YELLOW "🔍 Checking test collection..."
if ! python -m pytest --collect-only -q tests/integration/ >/dev/null 2>&1; then
    print_status $RED "❌ Test collection failed"
    print_status $YELLOW "💡 Run 'python -m pytest --collect-only tests/integration/' to see details"
    exit 1
fi

# Check if test utilities can be imported
print_status $YELLOW "🔍 Checking test utilities..."
if ! python -c "
import sys
sys.path.append('tests')
try:
    from support.message_spy import CollectionPhaseSpy
    from support.db_cleanup import CollectionPhaseCleanup
    from support.event_publisher import TestEventFactory
    from support.test_environment import CollectionPhaseTestEnvironment
    print('Test utilities import OK')
except ImportError as e:
    print(f'Import error: {e}')
    sys.exit(1)
" 2>/dev/null; then
    print_status $RED "❌ Test utilities import failed"
    exit 1
fi

# Check if configuration files are valid
print_status $YELLOW "🔍 Checking configuration files..."
if [ -f "pytest.ini" ] && ! python -c "
import configparser
config = configparser.ConfigParser()
config.read('pytest.ini')
if 'pytest' not in config:
    print('pytest.ini missing [pytest] section')
    exit(1)
print('pytest.ini OK')
" 2>/dev/null; then
    print_status $RED "❌ pytest.ini configuration error"
    exit 1
fi

# Run a quick syntax check on key test files
print_status $YELLOW "🔍 Running quick syntax check on key test files..."
key_test_files=(
    "tests/integration/test_collection_phase_happy_path.py"
    "tests/integration/test_collection_phase_integration.py"
    "tests/integration/test_observability_validation.py"
)

for file in "${key_test_files[@]}"; do
    if [ -f "$file" ]; then
        if ! python -c "
import ast
with open('$file', 'r') as f:
    try:
        ast.parse(f.read())
        print('✅ $file syntax OK')
    except SyntaxError as e:
        print(f'❌ Syntax error in $file: {e}')
        exit(1)
" 2>/dev/null; then
            print_status $RED "❌ Syntax check failed for $file"
            exit 1
        fi
    fi
done

print_status $GREEN "✅ All pre-commit test validations passed!"
print_status $GREEN "🚀 Ready to commit!"

exit 0
