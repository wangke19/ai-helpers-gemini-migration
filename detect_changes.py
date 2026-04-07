#!/usr/bin/env python3
"""
Detect changes between ai-helpers plugins and gemini-ai-helpers extensions.
Identifies new plugins, updated plugins, and unchanged plugins.
"""

import os
import re
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Set

SOURCE_DIR = Path("ai-helpers/plugins")
TARGET_DIR = Path("gemini-ai-helpers/extensions")
STATE_FILE = Path("migration_state.json")
CHANGES_FILE = Path("migration_changes.json")


def clean_claude_references(text: str) -> str:
    """Apply the same Claude→Gemini replacements as the migration script."""
    replacements = {
        r'\bClaude Code\b': 'Gemini CLI',
        r'\bClaude\b': 'Gemini',
        r'\bAnthropic\b': 'Google',
        r'\bAnthropic API\b': 'Gemini API',
        r'\b@anthropic-ai/sdk\b': '@google/generative-ai',
        r'\banthropicai\b': 'google-genai',
        r'\bCLAUDE_PLUGIN_ROOT\b': 'GEMINI_EXTENSION_ROOT',
        r'\bCLAUDE_API_KEY\b': 'GEMINI_API_KEY',
        r'\bplugin\.json\b': 'extension.json',
        r'\bplugins/\b': 'extensions/',
        r'\b/plugins/\b': '/extensions/',
        r'\bclaude\s+plugins?\b': 'gemini extensions',
        r'\bclaude\s+extensions?\b': 'gemini extensions',
    }
    result = text
    for pattern, replacement in replacements.items():
        result = re.sub(pattern, replacement, result)
    return result


def compute_plugin_hash(plugin_path: Path, clean: bool = False) -> str:
    """Compute MD5 hash of all files in plugin directory.

    If clean=True, apply Claude→Gemini replacements before hashing
    (used for source files to match the cleaned target).
    """
    hasher = hashlib.md5()

    for root, dirs, files in sorted(os.walk(plugin_path)):
        dirs.sort()
        for file in sorted(files):
            file_path = Path(root) / file
            if file_path.is_file():
                if clean and file.endswith(('.md', '.json', '.yaml', '.yml', '.toml', '.txt')):
                    content = file_path.read_text()
                    content = clean_claude_references(content)
                    hasher.update(content.encode())
                else:
                    with open(file_path, 'rb') as f:
                        hasher.update(f.read())

    return hasher.hexdigest()


def get_plugin_list(base_dir: Path) -> Set[str]:
    """Get list of all plugin/extension names."""
    if not base_dir.exists():
        return set()

    return {p.name for p in base_dir.iterdir() if p.is_dir()}


def detect_changes() -> Dict:
    """Detect new, updated, and unchanged plugins."""

    # Get current plugin lists
    source_plugins = get_plugin_list(SOURCE_DIR)
    target_plugins = get_plugin_list(TARGET_DIR)

    # Categorize plugins
    new_plugins = source_plugins - target_plugins
    removed_plugins = target_plugins - source_plugins
    common_plugins = source_plugins & target_plugins

    # Check for changes in common plugins
    updated_plugins = []
    unchanged_plugins = []

    for plugin in sorted(common_plugins):
        source_hash = compute_plugin_hash(SOURCE_DIR / plugin, clean=True)
        target_hash = compute_plugin_hash(TARGET_DIR / plugin)

        if source_hash != target_hash:
            updated_plugins.append(plugin)
        else:
            unchanged_plugins.append(plugin)

    results = {
        "new_plugins": sorted(list(new_plugins)),
        "updated_plugins": sorted(updated_plugins),
        "unchanged_plugins": sorted(unchanged_plugins),
        "removed_plugins": sorted(list(removed_plugins)),
        "source_total": len(source_plugins),
        "target_total": len(target_plugins),
        "needs_migration": sorted(list(new_plugins) + updated_plugins)
    }

    return results


def main():
    print("🔍 Detecting changes between ai-helpers and gemini-ai-helpers...")
    print()

    results = detect_changes()

    # Save results
    with open(CHANGES_FILE, 'w') as f:
        json.dump(results, f, indent=2)

    # Print summary
    print(f"📊 Summary:")
    print(f"  Source plugins (ai-helpers):     {results['source_total']}")
    print(f"  Target extensions (gemini):      {results['target_total']}")
    print()
    print(f"  ✨ New plugins:                  {len(results['new_plugins'])}")
    print(f"  🔄 Updated plugins:              {len(results['updated_plugins'])}")
    print(f"  ✅ Unchanged plugins:            {len(results['unchanged_plugins'])}")
    print(f"  🗑️  Removed from target:         {len(results['removed_plugins'])}")
    print()
    print(f"  📦 Total needing migration:      {len(results['needs_migration'])}")
    print()

    if results['new_plugins']:
        print("✨ New plugins:")
        for plugin in results['new_plugins']:
            print(f"  - {plugin}")
        print()

    if results['updated_plugins']:
        print("🔄 Updated plugins:")
        for plugin in results['updated_plugins']:
            print(f"  - {plugin}")
        print()

    if results['removed_plugins']:
        print("⚠️  Plugins in target but not in source:")
        for plugin in results['removed_plugins']:
            print(f"  - {plugin}")
        print()

    print(f"💾 Results saved to: {CHANGES_FILE}")


if __name__ == "__main__":
    main()
