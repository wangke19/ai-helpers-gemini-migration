#!/usr/bin/env python3
"""
Generate comprehensive migration report before switching main branch.
This report helps decide whether to proceed with the migration.
"""

import os
import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple


# Directories
GEMINI_REPO = Path("gemini-ai-helpers")
STATE_FILE = Path("migration_state.json")
CHANGES_FILE = Path("migration_changes.json")


def git_run(args: List[str]) -> subprocess.CompletedProcess:
    """Run git command in gemini-ai-helpers repo."""
    return subprocess.run(
        ["git"] + args,
        cwd=GEMINI_REPO,
        capture_output=True,
        text=True
    )


def get_current_branch() -> str:
    """Get current git branch."""
    result = git_run(["rev-parse", "--abbrev-ref", "HEAD"])
    return result.stdout.strip()


def get_commit_count(branch: str) -> int:
    """Get number of commits on a branch."""
    result = git_run(["rev-list", "--count", branch])
    return int(result.stdout.strip()) if result.returncode == 0 else 0


def get_commits_since_main(branch: str) -> List[Dict]:
    """Get commits on branch that are not in main."""
    result = git_run(["log", "main..{}".format(branch), "--oneline", "--no-decorate"])
    if result.returncode != 0:
        return []

    commits = []
    for line in result.stdout.strip().split('\n'):
        if line:
            parts = line.split(' ', 1)
            commits.append({
                "hash": parts[0],
                "message": parts[1] if len(parts) > 1 else ""
            })
    return commits


def get_changed_files(branch: str) -> List[str]:
    """Get files changed on branch compared to main."""
    result = git_run(["diff", "--name-only", "main", branch])
    if result.returncode != 0:
        return []
    return [f for f in result.stdout.strip().split('\n') if f]


def get_migration_stats(commits: List[Dict]) -> Dict:
    """Extract migration statistics from commits."""
    stats = {
        "total_commits": len(commits),
        "plugin_migrations": 0,
        "new_plugins": [],
        "updated_plugins": [],
        "failed_migrations": 0
    }

    for commit in commits:
        msg = commit["message"]
        if "feat: migrate" in msg:
            stats["plugin_migrations"] += 1
            # Extract plugin name
            if "plugin from" in msg:
                plugin_name = msg.split("feat: migrate")[1].split("plugin from")[0].strip()
                stats["updated_plugins"].append(plugin_name)

    return stats


def check_toml_files() -> Dict:
    """Check TOML files validation status."""
    result = subprocess.run(
        ["python3", "-m", "aihelpers.validate_toml"],
        capture_output=True,
        text=True
    )

    return {
        "passed": result.returncode == 0,
        "output": result.stdout,
        "errors": result.stderr
    }


def check_compatibility() -> Dict:
    """Check for Claude/Anthropic references."""
    issues = []

    # Check all extensions
    for plugin_dir in (GEMINI_REPO / "extensions").iterdir():
        if plugin_dir.is_dir():
            result = subprocess.run(
                ["python3", "-m", "aihelpers.gemini_compat_check", plugin_dir.name],
                capture_output=True,
                text=True
            )
            if result.returncode != 0 or "issues found" in result.stdout.lower():
                issues.append({
                    "plugin": plugin_dir.name,
                    "output": result.stdout
                })

    return {
        "clean": len(issues) == 0,
        "issues": issues
    }


def get_file_stats(changed_files: List[str]) -> Dict:
    """Analyze changed files."""
    stats = {
        "total": len(changed_files),
        "extensions": 0,
        "commands": 0,
        "other": 0,
        "by_type": {}
    }

    for f in changed_files:
        if f.startswith("extensions/"):
            stats["extensions"] += 1
        elif f.startswith("commands/"):
            stats["commands"] += 1
        else:
            stats["other"] += 1

        # Count by extension
        ext = Path(f).suffix or "no_ext"
        stats["by_type"][ext] = stats["by_type"].get(ext, 0) + 1

    return stats


def load_migration_state() -> Dict:
    """Load migration state."""
    if STATE_FILE.exists():
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {}


def load_changes() -> Dict:
    """Load change detection results."""
    if CHANGES_FILE.exists():
        with open(CHANGES_FILE, 'r') as f:
            return json.load(f)
    return {}


def generate_report(branch_name: str, output_file: str = None) -> str:
    """Generate comprehensive migration report."""

    report_lines = []

    def add(line: str = ""):
        report_lines.append(line)

    # Header
    add("=" * 80)
    add("MIGRATION REPORT - PRE-SWITCH VALIDATION")
    add("=" * 80)
    add()
    add(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    add(f"Branch:    {branch_name}")
    add()

    # Current state
    current_branch = get_current_branch()
    add("─" * 80)
    add("CURRENT STATE")
    add("─" * 80)
    add(f"Current branch:  {current_branch}")
    add(f"Target branch:   {branch_name}")
    add()

    if current_branch != branch_name:
        add("⚠️  WARNING: Not on target migration branch!")
        add(f"   Expected: {branch_name}")
        add(f"   Actual:   {current_branch}")
        add()

    # Commits analysis
    add("─" * 80)
    add("COMMITS ANALYSIS")
    add("─" * 80)

    commits = get_commits_since_main(branch_name)
    stats = get_migration_stats(commits)

    add(f"Total commits:        {stats['total_commits']}")
    add(f"Plugin migrations:    {stats['plugin_migrations']}")
    add()

    if commits:
        add("Commits on migration branch:")
        for i, commit in enumerate(commits[:20], 1):  # Show first 20
            add(f"  {i:2d}. {commit['hash']} {commit['message']}")

        if len(commits) > 20:
            add(f"  ... and {len(commits) - 20} more")
        add()

    # Migrated plugins
    if stats['updated_plugins']:
        add("Plugins migrated:")
        for i, plugin in enumerate(stats['updated_plugins'][:30], 1):
            add(f"  {i:2d}. {plugin}")
        if len(stats['updated_plugins']) > 30:
            add(f"  ... and {len(stats['updated_plugins']) - 30} more")
        add()

    # Changed files
    add("─" * 80)
    add("FILES CHANGED")
    add("─" * 80)

    changed_files = get_changed_files(branch_name)
    file_stats = get_file_stats(changed_files)

    add(f"Total files changed:  {file_stats['total']}")
    add(f"  Extensions:         {file_stats['extensions']}")
    add(f"  Commands (TOML):    {file_stats['commands']}")
    add(f"  Other:              {file_stats['other']}")
    add()

    add("Files by type:")
    for ext, count in sorted(file_stats['by_type'].items(), key=lambda x: -x[1])[:10]:
        add(f"  {ext:15s} {count:5d}")
    add()

    # TOML validation
    add("─" * 80)
    add("TOML VALIDATION")
    add("─" * 80)

    toml_check = check_toml_files()
    if toml_check['passed']:
        add("✅ All TOML files validated successfully")
    else:
        add("❌ TOML validation FAILED")
        add()
        add("Validation output:")
        for line in toml_check['output'].split('\n')[:20]:
            add(f"  {line}")
        if toml_check['errors']:
            add()
            add("Errors:")
            for line in toml_check['errors'].split('\n')[:20]:
                add(f"  {line}")
    add()

    # Compatibility check
    add("─" * 80)
    add("COMPATIBILITY CHECK")
    add("─" * 80)

    compat = check_compatibility()
    if compat['clean']:
        add("✅ No Claude/Anthropic references found")
    else:
        add(f"⚠️  Found {len(compat['issues'])} plugin(s) with compatibility issues")
        add()
        for issue in compat['issues'][:10]:
            add(f"Plugin: {issue['plugin']}")
            add("Issues:")
            for line in issue['output'].split('\n')[:5]:
                if line.strip():
                    add(f"  {line}")
            add()
    add()

    # Migration state
    add("─" * 80)
    add("MIGRATION STATE")
    add("─" * 80)

    state = load_migration_state()
    if state:
        add(f"Completed plugins:  {len(state.get('completed_plugins', []))}")
        add(f"Failed plugins:     {len(state.get('failed_plugins', []))}")
        add(f"Last migration:     {state.get('last_migration', 'Never')}")
        add(f"Last tag:           {state.get('last_tag', 'None')}")

        if state.get('failed_plugins'):
            add()
            add("Failed plugins:")
            for plugin in state['failed_plugins']:
                add(f"  - {plugin}")
    else:
        add("No migration state found")
    add()

    # Change detection summary
    add("─" * 80)
    add("CHANGE DETECTION SUMMARY")
    add("─" * 80)

    changes = load_changes()
    if changes:
        add(f"New plugins:        {len(changes.get('new_plugins', []))}")
        add(f"Updated plugins:    {len(changes.get('updated_plugins', []))}")
        add(f"Unchanged plugins:  {len(changes.get('unchanged_plugins', []))}")
        add(f"Total source:       {changes.get('source_total', 0)}")
        add(f"Total target:       {changes.get('target_total', 0)}")

        if changes.get('new_plugins'):
            add()
            add("New plugins:")
            for plugin in changes['new_plugins']:
                add(f"  - {plugin}")
    else:
        add("No change detection data found")
    add()

    # Pre-flight checks
    add("=" * 80)
    add("PRE-FLIGHT CHECKS")
    add("=" * 80)

    checks = []

    # Check 1: Branch exists
    result = git_run(["rev-parse", "--verify", branch_name])
    checks.append({
        "name": "Migration branch exists",
        "passed": result.returncode == 0,
        "critical": True
    })

    # Check 2: TOML validation
    checks.append({
        "name": "TOML files valid",
        "passed": toml_check['passed'],
        "critical": True
    })

    # Check 3: Has commits
    checks.append({
        "name": "Has migration commits",
        "passed": len(commits) > 0,
        "critical": True
    })

    # Check 4: No failed plugins
    checks.append({
        "name": "No failed migrations",
        "passed": len(state.get('failed_plugins', [])) == 0,
        "critical": False
    })

    # Check 5: Compatibility
    checks.append({
        "name": "Compatibility clean",
        "passed": compat['clean'],
        "critical": False
    })

    # Check 6: Main branch clean
    result = git_run(["diff-index", "--quiet", "HEAD", "--"])
    checks.append({
        "name": "Working directory clean",
        "passed": result.returncode == 0,
        "critical": True
    })

    critical_pass = all(c['passed'] for c in checks if c['critical'])
    all_pass = all(c['passed'] for c in checks)

    for check in checks:
        status = "✅" if check['passed'] else ("🔴" if check['critical'] else "⚠️")
        critical_marker = " [CRITICAL]" if check['critical'] and not check['passed'] else ""
        add(f"{status} {check['name']}{critical_marker}")

    add()
    add("─" * 80)

    # Recommendation
    add()
    add("=" * 80)
    add("RECOMMENDATION")
    add("=" * 80)

    if critical_pass and all_pass:
        add("✅ PROCEED - All checks passed")
        add()
        add("The migration is ready to be applied to main branch.")
        add("All critical and optional checks passed successfully.")
        recommendation = "PROCEED"
    elif critical_pass:
        add("⚠️  PROCEED WITH CAUTION - Critical checks passed, warnings present")
        add()
        add("Critical checks passed, but some warnings were found.")
        add("Review the warnings above before proceeding.")
        recommendation = "CAUTION"
    else:
        add("🔴 DO NOT PROCEED - Critical checks failed")
        add()
        add("One or more critical checks failed. DO NOT switch main branch.")
        add("Fix the issues above before proceeding with the migration.")
        recommendation = "ABORT"

    add()
    add("=" * 80)
    add()

    # Next steps
    add("NEXT STEPS")
    add("─" * 80)

    if recommendation == "PROCEED":
        add("1. Review this report carefully")
        add("2. If satisfied, proceed with:")
        add(f"   git checkout main")
        add(f"   git reset --hard {branch_name}")
        add(f"   git push origin main --force-with-lease")
        add(f"   git push origin --tags")
    elif recommendation == "CAUTION":
        add("1. Review warnings above")
        add("2. Decide if warnings are acceptable")
        add("3. If acceptable, proceed as normal")
        add("4. If not, fix issues and regenerate report")
    else:  # ABORT
        add("1. DO NOT proceed with switching main")
        add("2. Fix critical issues listed above")
        add("3. Regenerate report after fixes")
        add("4. Only proceed when all critical checks pass")

    add()
    add("=" * 80)

    # Generate report text
    report_text = '\n'.join(report_lines)

    # Save to file if specified
    if output_file:
        with open(output_file, 'w') as f:
            f.write(report_text)
        print(f"Report saved to: {output_file}")

    return report_text


def main():
    import sys

    # Get branch name from command line or current branch
    if len(sys.argv) > 1:
        branch_name = sys.argv[1]
    else:
        branch_name = get_current_branch()

    # Generate output filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"migration_report_{timestamp}.txt"

    print(f"Generating migration report for branch: {branch_name}")
    print()

    # Generate and display report
    report = generate_report(branch_name, output_file)
    print(report)

    print()
    print(f"Full report saved to: {output_file}")


if __name__ == "__main__":
    main()
