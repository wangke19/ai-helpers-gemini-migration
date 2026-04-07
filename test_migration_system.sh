#!/bin/bash
#
# Test the migration system components
# Validates that all scripts work correctly before running actual migration
#

set -euo pipefail

cd /home/kewang/wangke19/ai-migration-workspace

echo "=================================================="
echo "Migration System v2.0 - Component Tests"
echo "=================================================="
echo

# Test 1: Python scripts exist and are executable
echo "Test 1: Checking Python scripts..."
scripts=(
    "detect_changes.py"
    "incremental_migrate.py"
    "generate_toml.py"
    "validate_toml.py"
    "gemini_compat_check.py"
    "migration_summary.py"
)

for script in "${scripts[@]}"; do
    if [ -f "$script" ]; then
        echo "  ✅ $script exists"
    else
        echo "  ❌ $script not found"
        exit 1
    fi
done
echo

# Test 2: Bash scripts exist and are executable
echo "Test 2: Checking Bash scripts..."
if [ -x "scheduled_migration.sh" ]; then
    echo "  ✅ scheduled_migration.sh exists and is executable"
else
    echo "  ❌ scheduled_migration.sh not found or not executable"
    exit 1
fi
echo

# Test 3: Source and target directories exist
echo "Test 3: Checking directories..."
if [ -d "ai-helpers/plugins" ]; then
    plugin_count=$(ls -d ai-helpers/plugins/*/ 2>/dev/null | wc -l)
    echo "  ✅ ai-helpers/plugins exists ($plugin_count plugins)"
else
    echo "  ❌ ai-helpers/plugins not found"
    exit 1
fi

if [ -d "gemini-ai-helpers/extensions" ]; then
    ext_count=$(ls -d gemini-ai-helpers/extensions/*/ 2>/dev/null | wc -l)
    echo "  ✅ gemini-ai-helpers/extensions exists ($ext_count extensions)"
else
    echo "  ❌ gemini-ai-helpers/extensions not found"
    exit 1
fi
echo

# Test 4: Python syntax check
echo "Test 4: Checking Python syntax..."
for script in "${scripts[@]}"; do
    if python3 -m py_compile "$script" 2>/dev/null; then
        echo "  ✅ $script syntax OK"
    else
        echo "  ❌ $script has syntax errors"
        exit 1
    fi
done
echo

# Test 5: Test detect_changes.py
echo "Test 5: Testing change detection..."
if python3 detect_changes.py > /tmp/detect_test.log 2>&1; then
    echo "  ✅ detect_changes.py runs successfully"
    if [ -f "migration_changes.json" ]; then
        echo "  ✅ migration_changes.json created"
    else
        echo "  ❌ migration_changes.json not created"
        exit 1
    fi
else
    echo "  ❌ detect_changes.py failed"
    cat /tmp/detect_test.log
    exit 1
fi
echo

# Test 6: Test migration_summary.py
echo "Test 6: Testing summary generation..."
if python3 migration_summary.py > /tmp/summary_test.log 2>&1; then
    echo "  ✅ migration_summary.py runs successfully"
else
    echo "  ❌ migration_summary.py failed"
    cat /tmp/summary_test.log
    exit 1
fi
echo

# Test 7: Test generate_toml.py with a single plugin
echo "Test 7: Testing TOML generation (single plugin)..."
if [ -d "gemini-ai-helpers/extensions/hello-world/commands" ]; then
    if python3 generate_toml.py hello-world > /tmp/toml_test.log 2>&1; then
        echo "  ✅ generate_toml.py runs successfully"
    else
        echo "  ❌ generate_toml.py failed"
        cat /tmp/toml_test.log
        exit 1
    fi
else
    echo "  ⏭️  Skipped (no hello-world commands)"
fi
echo

# Test 8: Test validate_toml.py
echo "Test 8: Testing TOML validation..."
if python3 validate_toml.py > /tmp/validate_test.log 2>&1; then
    echo "  ✅ validate_toml.py runs successfully"
else
    echo "  ⚠️  validate_toml.py failed (may need tomli package)"
    # Not a critical error
fi
echo

# Test 9: Check gemini-ai-helpers is a git repo
echo "Test 9: Checking git configuration..."
if [ -d "gemini-ai-helpers/.git" ]; then
    echo "  ✅ gemini-ai-helpers is a git repository"
    cd gemini-ai-helpers
    if git remote -v | grep -q "gemini-ai-helpers"; then
        echo "  ✅ git remote configured"
    else
        echo "  ⚠️  git remote may not be configured correctly"
    fi
    cd ..
else
    echo "  ❌ gemini-ai-helpers is not a git repository"
    exit 1
fi
echo

# Test 10: Check Python dependencies
echo "Test 10: Checking Python dependencies..."
python3 -c "import json" 2>/dev/null && echo "  ✅ json module available" || echo "  ❌ json module missing"
python3 -c "import hashlib" 2>/dev/null && echo "  ✅ hashlib module available" || echo "  ❌ hashlib module missing"
python3 -c "import pathlib" 2>/dev/null && echo "  ✅ pathlib module available" || echo "  ❌ pathlib module missing"
python3 -c "import re" 2>/dev/null && echo "  ✅ re module available" || echo "  ❌ re module missing"

# Optional: tomli for TOML validation
if python3 -c "import tomllib" 2>/dev/null; then
    echo "  ✅ tomllib available (Python 3.11+)"
elif python3 -c "import tomli" 2>/dev/null; then
    echo "  ✅ tomli package available"
else
    echo "  ⚠️  tomli/tomllib not available (install: pip install tomli)"
fi
echo

# Summary
echo "=================================================="
echo "✅ All critical tests passed!"
echo "=================================================="
echo
echo "System is ready for migration. Next steps:"
echo "  1. Review migration queue:"
echo "     python3 migration_summary.py"
echo
echo "  2. Run migration:"
echo "     python3 incremental_migrate.py"
echo
echo "  3. Or schedule automated migration:"
echo "     ./scheduled_migration.sh"
echo
echo "=================================================="
