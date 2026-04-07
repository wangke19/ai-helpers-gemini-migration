#!/bin/bash
#
# Scheduled migration runner v2.2 with approval workflow
#
# Workflow:
# 1. Update source (git pull ai-helpers)
# 2. Detect changes
# 3. Create migration branch
# 4. Migrate plugins one by one on the branch
# 5. Tag the migration branch
# 6. Generate comprehensive report
# 7. Auto-approve only if all checks pass (PROCEED)
# 8. Switch main to the tag
# 9. Push main and tags
# 10. Delete migration branch
#
# Can be scheduled via cron:
#   0 0 1,15 * * MIGRATION_AUTOMATED=true /path/to/scheduled_migration_v3.sh
#   (runs on 1st and 15th of each month at midnight)

set -euo pipefail

WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$WORKSPACE_DIR"

# Set automated mode
export MIGRATION_AUTOMATED=true

echo "=================================================="
echo "AI Helpers Scheduled Migration v2.2"
echo "With Pre-Switch Approval"
echo "$(date)"
echo "=================================================="
echo

# Step 1: Update ai-helpers source
echo "📥 Updating ai-helpers source repository..."
cd ai-helpers
git fetch origin
git pull origin main
cd ..
echo "✅ Source updated"
echo

# Step 2: Detect changes
echo "🔍 Detecting changes..."
python3 -m aihelpers.detect_changes
echo

# Step 3: Check if migration is needed
NEEDS_MIGRATION=$(python3 -c "
import json
with open('migration_changes.json', 'r') as f:
    data = json.load(f)
print(len(data['needs_migration']))
")

if [ "$NEEDS_MIGRATION" -eq 0 ]; then
    echo "✅ No plugins need migration. Everything is up to date!"
    exit 0
fi

echo "📦 Found $NEEDS_MIGRATION plugin(s) needing migration"
echo

# Step 4: Run migration with approval workflow
echo "🚀 Starting incremental migration with approval workflow..."
python3 -m aihelpers.incremental_migrate
MIGRATION_EXIT=$?

if [ $MIGRATION_EXIT -ne 0 ]; then
    echo "⚠️  Migration script exited with error code $MIGRATION_EXIT"

    # Check if migration was aborted (exit code 1 is typically user abort)
    if [ $MIGRATION_EXIT -eq 1 ]; then
        echo ""
        echo "Migration was likely aborted due to failed checks."
        echo "Check the migration report for details."
        echo ""

        # Find and display latest report
        LATEST_REPORT=$(ls -t migration_report_*.txt 2>/dev/null | head -1)
        if [ -n "$LATEST_REPORT" ]; then
            echo "Latest migration report: $LATEST_REPORT"
            echo ""
            echo "To review:"
            echo "  cat $LATEST_REPORT"
            echo ""
        fi
    fi

    exit $MIGRATION_EXIT
fi

echo

# Step 5: Verify main branch is at the right tag
echo "🔍 Verifying main branch..."
cd gemini-ai-helpers

CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo "⚠️  Not on main branch after migration: $CURRENT_BRANCH"
    echo "   Manual intervention needed"
    exit 1
fi

LATEST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "")
if [ -z "$LATEST_TAG" ]; then
    echo "⚠️  No tags found after migration"
else:
    echo "✅ Main branch is at tag: $LATEST_TAG"
fi

cd ..
echo

# Step 6: Summary report
echo "=================================================="
echo "Migration Summary Report"
echo "$(date)"
echo "=================================================="
python3 -c "
import json
from pathlib import Path

changes_file = Path('migration_changes.json')
state_file = Path('migration_state_v2.json')

if changes_file.exists():
    with open(changes_file, 'r') as f:
        changes = json.load(f)
    print(f'New plugins:     {len(changes[\"new_plugins\"])}')
    print(f'Updated plugins: {len(changes[\"updated_plugins\"])}')
    print(f'Unchanged:       {len(changes[\"unchanged_plugins\"])}')

if state_file.exists():
    with open(state_file, 'r') as f:
        state = json.load(f)
    print(f'Total completed: {len(state[\"completed_plugins\"])}')
    print(f'Failed:          {len(state[\"failed_plugins\"])}')
    print(f'Last migration:  {state.get(\"last_migration\", \"Never\")}')
    print(f'Last tag:        {state.get(\"last_tag\", \"None\")}')
"

echo
echo "=================================================="

# Step 7: Archive migration report
LATEST_REPORT=$(ls -t migration_report_*.txt 2>/dev/null | head -1)
if [ -n "$LATEST_REPORT" ]; then
    # Create reports directory if it doesn't exist
    mkdir -p migration_reports

    # Move report to archive
    mv "$LATEST_REPORT" migration_reports/
    echo "📄 Migration report archived: migration_reports/$(basename $LATEST_REPORT)"
fi

echo
echo "=================================================="
echo "✅ Scheduled migration completed successfully"
echo "=================================================="
