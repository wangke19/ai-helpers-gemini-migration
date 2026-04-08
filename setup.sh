#!/bin/bash
#
# One-time bootstrap: clone source repos and write migration.conf
#

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARENT_DIR="$(dirname "$PROJECT_DIR")"

AI_HELPERS_DIR="$PARENT_DIR/ai-helpers"
GEMINI_REPO_DIR="$PARENT_DIR/gemini-ai-helpers"

echo "Project dir : $PROJECT_DIR"
echo "Parent dir  : $PARENT_DIR"
echo

if [ -d "$AI_HELPERS_DIR" ]; then
    echo "✅ ai-helpers already exists: $AI_HELPERS_DIR"
else
    echo "📥 Cloning ai-helpers..."
    git clone git@github.com:openshift-eng/ai-helpers.git "$AI_HELPERS_DIR"
    echo "✅ ai-helpers cloned"
fi

if [ -d "$GEMINI_REPO_DIR" ]; then
    echo "✅ gemini-ai-helpers already exists: $GEMINI_REPO_DIR"
else
    echo "📥 Cloning gemini-ai-helpers..."
    git clone git@github.com:wangke19/gemini-ai-helpers.git "$GEMINI_REPO_DIR"
    echo "✅ gemini-ai-helpers cloned"
fi

cat > "$PROJECT_DIR/migration.conf" <<EOF
[repos]
ai_helpers_dir = $AI_HELPERS_DIR
gemini_repo_dir = $GEMINI_REPO_DIR
EOF

echo
echo "✅ migration.conf written:"
cat "$PROJECT_DIR/migration.conf"
echo
echo "Run: python3 -m aihelpers.incremental_migrate"
