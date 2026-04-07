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
from typing import List, Dict, Optional
from datetime import datetime


# Directories
SOURCE_DIR = Path("ai-helpers/plugins")
TARGET_DIR = Path("gemini-ai-helpers/extensions")
COMMANDS_DIR = Path("gemini-ai-helpers/commands")
GEMINI_REPO = Path("gemini-ai-helpers")
STATE_FILE = Path("migration_state_v2.json")
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
                ["python3", "generate_toml.py", plugin],
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
            ["python3", "validate_toml.py", plugin],
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
        # Check if there are changes
        result = git_run(["status", "--porcelain"], check=True)

        if not result.stdout.strip():
            print("   No changes to commit")
            return True

        # Add changes
        git_run(["add", f"extensions/{plugin}", f"commands/{plugin}"])

        # Commit
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
        ["python3", "validate_toml.py", plugin],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print(f"❌ TOML validation failed:\n{result.stderr}")
        return False

    # Test 3: Check for Claude/Anthropic references
    result = subprocess.run(
        ["python3", "gemini_compat_check.py", plugin],
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
        ["python3", "generate_migration_report.py", branch_name],
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


def switch_main_to_tag(version: str) -> bool:
    """Switch main branch to tag."""
    print(f"\n🔄 Switching main branch to tag: {version}")
    try:
        # Switch to main
        git_run(["checkout", "main"])

        # Reset main to the tag (hard reset)
        git_run(["reset", "--hard", version])
        print(f"✅ Main branch now points to: {version}")

        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to switch main: {e.stderr}")
        return False


def push_changes() -> bool:
    """Push main branch and tags to remote."""
    print(f"\n🚀 Pushing to remote...")
    try:
        # Push main (may need force since we reset it)
        result = git_run(["push", "origin", "main", "--force-with-lease"], check=False)
        if result.returncode != 0:
            print(f"⚠️  Force push with lease failed, trying regular push...")
            git_run(["push", "origin", "main"])

        # Push tags
        git_run(["push", "origin", "--tags"])

        print(f"✅ Changes pushed to remote")
        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to push: {e.stderr}")
        return False


def cleanup_migration_branch(version: str) -> bool:
    """Delete the migration branch after successful merge."""
    print(f"\n🧹 Cleaning up migration branch...")
    try:
        branch_name = f"migration-{version}"
        git_run(["branch", "-D", branch_name])
        print(f"✅ Deleted branch: {branch_name}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Failed to delete branch: {e.stderr}")
        return False


def main():
    print("🚀 AI Helpers Incremental Migration System v2.2")
    print("   (with pre-switch approval)")
    print("=" * 60)

    # Load change detection results
    if not CHANGES_FILE.exists():
        print("❌ Run detect_changes.py first to identify what needs migration")
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
    with open("gemini-ai-helpers/gemini-extension.json", 'r') as f:
        ext_data = json.load(f)
        current_version = ext_data.get('version', '1.0.0')

    # Parse semantic version and bump MINOR (e.g., 1.0.0 -> 1.1.0)
    parts = current_version.split('.')
    major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
    new_version = f"{major}.{minor + 1}.{patch}"

    # Get ai-helpers commit hash for traceability
    result = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd="ai-helpers",
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

    # Generate comprehensive report
    report, recommendation = generate_pre_switch_report(branch_name)

    # Request approval
    if not request_approval(report, recommendation):
        print()
        print("=" * 60)
        print("🛑 MIGRATION ABORTED BY USER")
        print("=" * 60)
        print()
        print(f"Migration branch and tag preserved: {branch_name}")
        print(f"Tag: {version}")
        print()
        print("To review the migration:")
        print(f"  cd gemini-ai-helpers")
        print(f"  git checkout {branch_name}")
        print(f"  git log")
        print()
        print("To proceed manually later:")
        print(f"  git checkout main")
        print(f"  git reset --hard {version}")
        print(f"  git push origin main --force-with-lease")
        print(f"  git push origin --tags")
        print()
        return

    # User approved - proceed with switching main
    print()
    print("=" * 60)
    print("✅ APPROVAL GRANTED - Proceeding with main branch switch")
    print("=" * 60)
    print()

    # Switch main to tag
    if switch_main_to_tag(version):
        # Push everything
        if push_changes():
            # Clean up migration branch
            cleanup_migration_branch(version)
            print(f"\n✅ Migration complete! Main branch now at tag {version}")
        else:
            print(f"\n⚠️  Tag created and main switched, but push failed. Manual push needed:")
            print(f"  cd gemini-ai-helpers")
            print(f"  git push origin main --force-with-lease")
            print(f"  git push origin --tags")
    else:
        print(f"\n⚠️  Failed to switch main. Migration branch and tag preserved for review.")

    print(f"\n💾 Migration state saved to: {STATE_FILE}")


if __name__ == "__main__":
    main()
