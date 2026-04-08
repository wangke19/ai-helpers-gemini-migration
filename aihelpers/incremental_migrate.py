#!/usr/bin/env python3
"""
Incremental migration system v2.2 with pre-switch approval.

Strategy:
1. Create migration branch from main
2. Migrate plugins one at a time
3. Generate comprehensive report
4. Request approval before switching main
5. After approval: tag, switch main, push
"""

import os
import re
import json
import shutil
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime


# Directories (resolved from migration.conf or env vars via aihelpers.config)
from aihelpers.config import SOURCE_DIR, SOURCE_REPO, TARGET_DIR, COMMANDS_DIR, GEMINI_REPO
STATE_FILE = Path("migration_state.json")
CHANGES_FILE = Path("migration_changes.json")

# Migration config
BATCH_SIZE = 1  # Migrate one plugin at a time for safety


class MigrationState:
    """Manages migration state and versioning."""

    def __init__(self, state_file: Path = STATE_FILE):
        self.state_file = state_file
        self.state = self._load_state()

    def _load_state(self) -> Dict:
        """Load migration state from file."""
        if self.state_file.exists():
            with open(self.state_file, 'r') as f:
                return json.load(f)

        return {
            "version": "2.2",
            "last_migration": None,
            "last_tag": None,
            "migrations": [],
            "completed_plugins": [],
            "failed_plugins": []
        }

    def save(self):
        """Save migration state to file."""
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)

    def record_migration(self, plugin: str, status: str, details: Optional[Dict] = None):
        """Record a migration attempt."""
        migration_record = {
            "plugin": plugin,
            "timestamp": datetime.now().isoformat(),
            "status": status,
            "details": details or {}
        }

        self.state["migrations"].append(migration_record)
        self.state["last_migration"] = datetime.now().isoformat()

        if status == "success":
            if plugin not in self.state["completed_plugins"]:
                self.state["completed_plugins"].append(plugin)
            # Remove from failed if it was previously failed
            if plugin in self.state["failed_plugins"]:
                self.state["failed_plugins"].remove(plugin)
        elif status == "failed":
            if plugin not in self.state["failed_plugins"]:
                self.state["failed_plugins"].append(plugin)

        self.save()

    def record_tag(self, tag: str):
        """Record a tag creation."""
        self.state["last_tag"] = tag
        self.save()


def clean_claude_references(text: str) -> str:
    """Replace Claude-specific terminology with Gemini equivalents."""
    replacements = {
        # Tool/API names
        r'\bClaude Code\b': 'Gemini CLI',
        r'\bClaude\b': 'Gemini',
        r'\bAnthropic\b': 'Google',
        r'\bAnthropic API\b': 'Gemini API',
        r'\b@anthropic-ai/sdk\b': '@google/generative-ai',
        r'\banthropicai\b': 'google-genai',

        # Environment variables
        r'\bCLAUDE_PLUGIN_ROOT\b': 'GEMINI_EXTENSION_ROOT',
        r'\bCLAUDE_API_KEY\b': 'GEMINI_API_KEY',

        # File/directory references
        r'\bplugin\.json\b': 'extension.json',
        r'\bplugins/\b': 'extensions/',
        r'\b/plugins/\b': '/extensions/',

        # Commands
        r'\bclaude\s+plugins?\b': 'gemini extensions',
        r'\bclaude\s+extensions?\b': 'gemini extensions',
    }

    result = text
    for pattern, replacement in replacements.items():
        result = re.sub(pattern, replacement, result)

    return result


def git_run(args: List[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run git command in gemini-ai-helpers repo."""
    return subprocess.run(
        ["git"] + args,
        cwd=GEMINI_REPO,
        capture_output=True,
        text=True,
        check=check
    )


def create_migration_branch(version: str) -> bool:
    """Create a new migration branch from main."""
    print(f"\n🌿 Creating migration branch: migration-{version}")
    try:
        # Ensure we're on main and it's clean
        git_run(["checkout", "main"])

        # Pull latest
        git_run(["pull", "origin", "main"])

        # Create new branch
        branch_name = f"migration-{version}"
        git_run(["checkout", "-b", branch_name])

        print(f"✅ Created and switched to branch: {branch_name}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to create migration branch: {e.stderr}")
        return False


def migrate_plugin(plugin: str, state: MigrationState) -> bool:
    """Migrate a single plugin."""
    print(f"\n{'='*60}")
    print(f"Migrating: {plugin}")
    print(f"{'='*60}")

    source_path = SOURCE_DIR / plugin
    target_path = TARGET_DIR / plugin

    if not source_path.exists():
        print(f"❌ Source plugin not found: {source_path}")
        state.record_migration(plugin, "failed", {"reason": "source_not_found"})
        return False

    try:
        # Step 1: Remove old version if exists
        if target_path.exists():
            print(f"🗑️  Removing old version: {target_path}")
            shutil.rmtree(target_path)

        # Step 2: Copy plugin to extensions
        print(f"📦 Copying {source_path} → {target_path}")
        shutil.copytree(source_path, target_path,
                        ignore=shutil.ignore_patterns('.claude-plugin'))

        # Step 3: Clean Claude references in all files
        print(f"🧹 Cleaning Claude/Anthropic references...")
        file_count = 0
        for root, dirs, files in os.walk(target_path):
            for file in files:
                if file.endswith(('.md', '.json', '.yaml', '.yml', '.toml', '.txt')):
                    file_path = Path(root) / file
                    try:
                        content = file_path.read_text()
                        cleaned = clean_claude_references(content)
                        if content != cleaned:
                            file_path.write_text(cleaned)
                            file_count += 1
                    except Exception as e:
                        print(f"⚠️  Warning: Could not clean {file_path}: {e}")

        print(f"   Cleaned {file_count} files")

        # Step 4: Generate TOML commands
        print(f"🔨 Generating TOML commands...")
        commands_path = target_path / "commands"
        if commands_path.exists():
            result = subprocess.run(
                ["python3", "-m", "aihelpers.generate_toml", plugin],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                print(f"⚠️  Warning: TOML generation had issues:\n{result.stderr}")
            else:
                print(f"   {result.stdout.strip()}")

        # Step 5: Validate TOML files
        print(f"✅ Validating TOML files...")
        result = subprocess.run(
            ["python3", "-m", "aihelpers.validate_toml", plugin],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"❌ TOML validation failed:\n{result.stderr}")
            state.record_migration(plugin, "failed", {"reason": "toml_validation_failed"})
            return False

        state.record_migration(plugin, "success")
        print(f"✅ Migration successful: {plugin}")
        return True

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        state.record_migration(plugin, "failed", {"reason": str(e)})
        return False


def commit_changes(plugin: str) -> bool:
    """Commit changes for a single plugin."""
    print(f"\n💾 Committing changes for: {plugin}")
    try:
        # Stage plugin-specific paths (ignore errors for missing paths e.g. no commands/ dir)
        git_run(["add", f"extensions/{plugin}"], check=False)
        git_run(["add", f"commands/{plugin}"], check=False)

        # Check if anything was actually staged
        result = git_run(["diff", "--cached", "--quiet"], check=False)
        if result.returncode == 0:
            print("   No changes to commit (already up to date)")
            return True

        message = f"feat: migrate {plugin} plugin from ai-helpers\n\nUpdated from upstream ai-helpers repository"
        git_run(["commit", "-m", message])

        print(f"✅ Changes committed")
        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to commit: {e.stderr}")
        return False


def run_sanity_tests(plugin: str) -> bool:
    """Run sanity tests for a migrated plugin."""
    print(f"\n🧪 Running sanity tests for: {plugin}")

    # Test 1: Check extension directory exists
    target_path = TARGET_DIR / plugin
    if not target_path.exists():
        print(f"❌ Extension directory not found: {target_path}")
        return False

    # Test 2: Validate TOML files
    result = subprocess.run(
        ["python3", "-m", "aihelpers.validate_toml", plugin],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print(f"❌ TOML validation failed:\n{result.stderr}")
        return False

    # Test 3: Check for Claude/Anthropic references
    result = subprocess.run(
        ["python3", "-m", "aihelpers.gemini_compat_check", plugin],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print(f"⚠️  Warning: Compatibility check issues:\n{result.stdout}")

    print(f"✅ Sanity tests passed")
    return True


def generate_pre_switch_report(branch_name: str) -> Tuple[str, str]:
    """
    Generate comprehensive migration report.
    Returns: (report_text, recommendation)
    recommendation is one of: "PROCEED", "CAUTION", "ABORT"
    """
    print(f"\n📊 Generating migration report...")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"migration_report_{timestamp}.txt"

    result = subprocess.run(
        ["python3", "-m", "aihelpers.generate_migration_report", branch_name],
        capture_output=True,
        text=True
    )

    # Read the generated report
    if Path(report_file).exists():
        with open(report_file, 'r') as f:
            report_text = f.read()
    else:
        # Use stdout as fallback
        report_text = result.stdout

    # Determine recommendation from report
    if "✅ PROCEED - All checks passed" in report_text:
        recommendation = "PROCEED"
    elif "⚠️  PROCEED WITH CAUTION" in report_text:
        recommendation = "CAUTION"
    else:
        recommendation = "ABORT"

    return report_text, recommendation


def request_approval(report: str, recommendation: str) -> bool:
    """
    Display report and request user approval.
    In automated mode, auto-approve only if recommendation is PROCEED.
    In interactive mode, always ask.
    """

    print("\n" + "="*80)
    print("MIGRATION REPORT GENERATED")
    print("="*80)
    print()
    print(report)
    print()
    print("="*80)
    print()

    # Check if running in automated mode
    automated = os.environ.get('MIGRATION_AUTOMATED', '').lower() == 'true'

    if automated:
        if recommendation == "PROCEED":
            print("✅ Automated mode: All checks passed, proceeding automatically")
            return True
        else:
            print(f"🔴 Automated mode: Recommendation is {recommendation}, aborting")
            return False

    # Interactive mode: always ask
    print("Do you want to proceed with switching main branch to this migration?")
    print()
    if recommendation == "PROCEED":
        print("Recommendation: ✅ PROCEED (all checks passed)")
    elif recommendation == "CAUTION":
        print("Recommendation: ⚠️  CAUTION (warnings present)")
    else:
        print("Recommendation: 🔴 ABORT (critical issues found)")
    print()

    while True:
        response = input("Proceed? [yes/no/view]: ").strip().lower()

        if response in ['yes', 'y']:
            return True
        elif response in ['no', 'n']:
            return False
        elif response in ['view', 'v']:
            print("\n" + report + "\n")
        else:
            print("Please answer 'yes', 'no', or 'view'")


def create_tag_only(version: str, message: str, state: MigrationState) -> bool:
    """Create tag on current branch without switching main yet."""
    print(f"\n🏷️  Creating tag: {version}")
    try:
        # Create annotated tag
        git_run(["tag", "-a", version, "-m", message])
        print(f"✅ Tag created: {version}")

        state.record_tag(version)
        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to create tag: {e.stderr}")
        return False


def pull_source() -> bool:
    """Pull latest changes from ai-helpers upstream."""
    print(f"\n📥 Pulling latest ai-helpers...")
    try:
        result = subprocess.run(
            ["git", "pull", "origin", "main"],
            cwd=SOURCE_REPO,
            capture_output=True,
            text=True,
            check=True,
        )
        print(f"✅ ai-helpers updated: {result.stdout.strip().splitlines()[-1]}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to pull ai-helpers: {e.stderr}")
        return False


def push_branch_and_open_pr(branch_name: str, version: str, migrated_count: int,
                             source_commit: str) -> bool:
    """Push migration branch and open a GitHub PR."""
    print(f"\n🚀 Pushing migration branch: {branch_name}")
    try:
        git_run(["push", "-u", "origin", branch_name])
        print(f"✅ Branch pushed")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to push branch: {e.stderr}")
        return False

    print(f"\n📬 Opening pull request...")
    pr_title = f"feat: migrate {migrated_count} plugin(s) from ai-helpers ({version})"
    pr_body = (
        f"## Migration batch {version}\n\n"
        f"Automated migration of {migrated_count} plugin(s) from "
        f"[ai-helpers](https://github.com/openshift-eng/ai-helpers) "
        f"@ `{source_commit}`.\n\n"
        f"### What changed\n"
        f"- Claude/Anthropic references replaced with Gemini equivalents\n"
        f"- `.md` commands regenerated as `.toml` for Gemini CLI\n\n"
        f"### Review\n"
        f"- [ ] Check changed extensions look correct\n"
        f"- [ ] Verify TOML commands parse cleanly\n"
    )
    try:
        result = subprocess.run(
            ["gh", "pr", "create",
             "--title", pr_title,
             "--body", pr_body,
             "--base", "main",
             "--head", branch_name],
            cwd=GEMINI_REPO,
            capture_output=True,
            text=True,
            check=True,
        )
        pr_url = result.stdout.strip()
        print(f"✅ PR opened: {pr_url}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to open PR: {e.stderr}")
        print(f"   Branch {branch_name} is pushed — open the PR manually.")
        return False


def main():
    print("🚀 AI Helpers Incremental Migration System v2.2")
    print("=" * 60)

    # Step 0: Pull latest ai-helpers
    if not pull_source():
        print("❌ Failed to update source, aborting")
        return

    # Step 1: Detect changes
    print(f"\n🔍 Detecting changes...")
    subprocess.run(["python3", "-m", "aihelpers.detect_changes"], check=True)

    # Load change detection results
    if not CHANGES_FILE.exists():
        print("❌ Change detection did not produce migration_changes.json")
        return

    with open(CHANGES_FILE, 'r') as f:
        changes = json.load(f)

    plugins_to_migrate = changes['needs_migration']

    if not plugins_to_migrate:
        print("✅ No plugins need migration!")
        return

    print(f"\n📋 Plugins to migrate: {len(plugins_to_migrate)}")
    for plugin in plugins_to_migrate:
        marker = "✨" if plugin in changes['new_plugins'] else "🔄"
        print(f"  {marker} {plugin}")

    print(f"\n⚙️  Migration settings:")
    print(f"  Batch size: {BATCH_SIZE} plugin(s)")
    print()

    # Read current version from gemini-extension.json
    with open(GEMINI_REPO / "gemini-extension.json", 'r') as f:
        ext_data = json.load(f)
        current_version = ext_data.get('version', '1.0.0')

    # Parse semantic version and compute next version:
    #   - patch +1 each daily migration; at 10 → minor +1, patch resets to 0
    #   - minor at 10 → major +1, minor and patch reset to 0
    #   - if last migration was ≥14 days ago → minor +1, patch resets to 0
    parts = current_version.split('.')
    major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])

    last_migration_str = state.state.get('last_migration')
    gap_days = 0
    if last_migration_str:
        last_dt = datetime.fromisoformat(last_migration_str)
        gap_days = (datetime.now() - last_dt).days

    if gap_days >= 14:
        # Long gap — bump minor
        minor += 1
        patch = 0
        print(f"⏱️  {gap_days} days since last migration — bumping minor version")
    else:
        # Normal daily bump — increment patch, carry over at 10
        patch += 1
        if patch >= 10:
            patch = 0
            minor += 1
        if minor >= 10:
            minor = 0
            major += 1

    new_version = f"{major}.{minor}.{patch}"

    # Get ai-helpers commit hash for traceability
    result = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=SOURCE_REPO,
        capture_output=True,
        text=True
    )
    source_commit = result.stdout.strip() if result.returncode == 0 else "unknown"

    # Tag format: v1.1.0-c5abf42
    # Where: v1.1.0 = semantic version from gemini-extension.json (bumped)
    #        c5abf42 = ai-helpers source commit
    version = f"v{new_version}-{source_commit}"
    branch_name = f"migration-{version}"

    # Load state
    state = MigrationState()

    # Create migration branch
    if not create_migration_branch(version):
        print("❌ Failed to create migration branch, aborting")
        return

    # Migrate plugins one at a time
    migrated_count = 0
    failed_count = 0

    for plugin in plugins_to_migrate:
        # Migrate
        success = migrate_plugin(plugin, state)

        if success:
            # Run sanity tests
            if run_sanity_tests(plugin):
                # Commit
                if commit_changes(plugin):
                    migrated_count += 1
                    print(f"\n✅ {plugin} fully migrated and committed")
                else:
                    print(f"\n⚠️  {plugin} migrated but commit failed")
                    failed_count += 1
            else:
                print(f"\n❌ {plugin} failed sanity tests")
                failed_count += 1
        else:
            failed_count += 1

        print()

    # Summary
    print("\n" + "=" * 60)
    print("📊 Migration Summary")
    print("=" * 60)
    print(f"  ✅ Successfully migrated: {migrated_count}")
    print(f"  ❌ Failed:               {failed_count}")
    print(f"  📦 Total processed:      {migrated_count + failed_count}")
    print()

    # Only proceed with tagging if we had successful migrations
    if migrated_count == 0:
        print("\n⚠️  No successful migrations. Migration branch preserved for debugging.")
        print(f"\n💾 Migration state saved to: {STATE_FILE}")
        return

    # Update gemini-extension.json version
    print(f"\n📝 Updating gemini-extension.json version to {new_version}")
    try:
        ext_json_path = GEMINI_REPO / "gemini-extension.json"
        with open(ext_json_path, 'r') as f:
            ext_data = json.load(f)
        ext_data['version'] = new_version
        with open(ext_json_path, 'w') as f:
            json.dump(ext_data, f, indent=2)
            f.write('\n')  # Add trailing newline

        # Commit version update
        git_run(["add", "gemini-extension.json"])
        git_run(["commit", "-m", f"chore: bump version to {new_version}"])
        print(f"✅ Version updated and committed")
    except Exception as e:
        print(f"⚠️  Failed to update version: {e}")

    # Create tag on migration branch
    message = f"Migration batch: {migrated_count} plugins updated/added from ai-helpers@{source_commit}"
    if not create_tag_only(version, message, state):
        print(f"\n⚠️  Tag creation failed. Migration branch preserved for review.")
        return

    # Push branch and open PR
    push_branch_and_open_pr(branch_name, version, migrated_count, source_commit)

    print(f"\n💾 Migration state saved to: {STATE_FILE}")


if __name__ == "__main__":
    main()
