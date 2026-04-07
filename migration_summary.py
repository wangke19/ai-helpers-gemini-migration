#!/usr/bin/env python3
"""
Generate a visual summary of migration status.
"""

import json
from pathlib import Path
from datetime import datetime


def load_json(filepath):
    """Load JSON file if exists."""
    if Path(filepath).exists():
        with open(filepath, 'r') as f:
            return json.load(f)
    return None


def print_summary():
    """Print migration summary with visual indicators."""

    print("=" * 70)
    print("AI HELPERS MIGRATION SYSTEM v2.0 - STATUS SUMMARY")
    print("=" * 70)
    print()

    # Load data
    changes = load_json("migration_changes.json")
    state = load_json("migration_state_v2.json")

    if not changes:
        print("❌ No change detection data. Run: python3 detect_changes.py")
        return

    # Header
    print(f"📅 Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Repository Status
    print("📦 REPOSITORY STATUS")
    print("-" * 70)
    print(f"  Source (ai-helpers):          {changes['source_total']} plugins")
    print(f"  Target (gemini-ai-helpers):   {changes['target_total']} plugins")
    print()

    # Change Summary
    print("🔍 CHANGE DETECTION")
    print("-" * 70)
    new_count = len(changes['new_plugins'])
    updated_count = len(changes['updated_plugins'])
    unchanged_count = len(changes['unchanged_plugins'])
    removed_count = len(changes['removed_plugins'])
    total = new_count + updated_count + unchanged_count

    print(f"  ✨ New plugins:               {new_count:3d} / {total}  ({new_count*100//total if total else 0}%)")
    print(f"  🔄 Updated plugins:           {updated_count:3d} / {total}  ({updated_count*100//total if total else 0}%)")
    print(f"  ✅ Unchanged plugins:         {unchanged_count:3d} / {total}  ({unchanged_count*100//total if total else 0}%)")
    if removed_count > 0:
        print(f"  🗑️  Removed from target:      {removed_count:3d}")
    print()

    # Migration Queue
    needs_migration = len(changes['needs_migration'])
    print("📋 MIGRATION QUEUE")
    print("-" * 70)
    print(f"  Total needing migration:      {needs_migration} plugins")
    print()

    if needs_migration > 0:
        print("  Plugins to migrate:")
        for i, plugin in enumerate(changes['needs_migration'][:10], 1):
            marker = "✨" if plugin in changes['new_plugins'] else "🔄"
            print(f"    {i:2d}. {marker} {plugin}")

        if needs_migration > 10:
            print(f"    ... and {needs_migration - 10} more")
        print()

    # Migration History
    if state:
        print("📊 MIGRATION HISTORY")
        print("-" * 70)
        completed_count = len(state.get('completed_plugins', []))
        failed_count = len(state.get('failed_plugins', []))
        total_migrations = len(state.get('migrations', []))

        print(f"  Total migration attempts:     {total_migrations}")
        print(f"  ✅ Completed successfully:    {completed_count}")
        print(f"  ❌ Failed:                    {failed_count}")

        if state.get('last_migration'):
            last = datetime.fromisoformat(state['last_migration'])
            print(f"  🕒 Last migration:            {last.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print(f"  🕒 Last migration:            Never")
        print()

        # Recent migrations
        recent = state.get('migrations', [])[-5:]
        if recent:
            print("  Recent migrations:")
            for m in reversed(recent):
                timestamp = datetime.fromisoformat(m['timestamp']).strftime('%Y-%m-%d %H:%M')
                status_icon = "✅" if m['status'] == 'success' else "❌"
                print(f"    {status_icon} {m['plugin']:20s} - {timestamp}")
            print()

        # Failed plugins
        if failed_count > 0:
            print("  ⚠️  Failed plugins requiring attention:")
            for plugin in state['failed_plugins']:
                print(f"    - {plugin}")
            print()

    # Progress Bar
    if state:
        completed = len(state.get('completed_plugins', []))
        total_plugins = changes['source_total']
        progress = completed * 100 // total_plugins if total_plugins else 0
        bar_width = 50
        filled = bar_width * progress // 100
        bar = '█' * filled + '░' * (bar_width - filled)

        print("📈 OVERALL PROGRESS")
        print("-" * 70)
        print(f"  [{bar}] {progress}% ({completed}/{total_plugins})")
        print()

    # Next Steps
    print("🎯 NEXT STEPS")
    print("-" * 70)
    if needs_migration == 0:
        print("  ✅ All plugins up to date! No migration needed.")
    else:
        print(f"  1. Review the {needs_migration} plugin(s) needing migration")
        print("  2. Run: python3 incremental_migrate.py")
        print("  3. Verify: python3 validate_toml.py")
        print("  4. Push: cd gemini-ai-helpers && git push && git push --tags")
    print()

    print("=" * 70)


if __name__ == "__main__":
    print_summary()
