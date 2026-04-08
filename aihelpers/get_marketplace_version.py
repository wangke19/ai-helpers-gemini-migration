#!/usr/bin/env python3
"""
Extract marketplace version info from ai-helpers for migration tagging.
"""

import json
import hashlib
from pathlib import Path

from aihelpers.config import SOURCE_REPO
marketplace_file = SOURCE_REPO / ".claude-plugin" / "marketplace.json"

if not marketplace_file.exists():
    print("unknown")
    exit(1)

with open(marketplace_file, 'r') as f:
    data = json.load(f)

# Calculate a hash of all plugin versions to create a marketplace "snapshot" ID
version_string = ""
for plugin in sorted(data.get('plugins', []), key=lambda x: x['name']):
    version_string += f"{plugin['name']}:{plugin.get('version', '0.0.0')};"

# Create short hash (8 chars) of the version string
version_hash = hashlib.md5(version_string.encode()).hexdigest()[:8]

print(f"mkt-{version_hash}")
