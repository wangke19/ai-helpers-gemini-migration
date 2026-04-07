# Versioning Strategy

## Overview

The gemini-ai-helpers repository uses **semantic versioning** aligned with the ai-helpers source repository state.

## Version Format

**Tag format:** `v<MAJOR>.<MINOR>.<PATCH>-<commit>`

**Example:** `v1.1.0-c5abf42`

Where:
- `v1.1.0` = Semantic version from gemini-extension.json (auto-bumped)
- `c5abf42` = ai-helpers source commit hash (for traceability)

## Semantic Versioning Rules

### MAJOR.MINOR.PATCH

- **MAJOR** (1.x.x): Breaking changes or major restructuring
- **MINOR** (x.1.x): Bi-weekly migrations (new/updated plugins)
- **PATCH** (x.x.1): Hotfixes or minor updates between migrations

### Version Bumping

**Bi-weekly migrations:** Increment MINOR
```
1.0.0 → 1.1.0  (first bi-weekly migration)
1.1.0 → 1.2.0  (second bi-weekly migration)
1.2.0 → 1.3.0  (third bi-weekly migration)
```

**Hotfixes:** Increment PATCH
```
1.1.0 → 1.1.1  (fix for 1.1.0)
1.2.0 → 1.2.1  (fix for 1.2.0)
```

**Breaking changes:** Increment MAJOR
```
1.9.0 → 2.0.0  (major restructuring)
```

## Version Source of Truth

**gemini-extension.json** is the authoritative version source:

```json
{
  "name": "gemini-ai-helpers",
  "version": "1.1.0",
  ...
}
```

The migration system:
1. Reads current version from gemini-extension.json
2. Bumps MINOR version automatically (bi-weekly)
3. Updates gemini-extension.json
4. Creates git tag with new version + source commit

## Tag Traceability

Each tag references the ai-helpers source commit:

```
v1.1.0-c5abf42
       └─────┘
       ai-helpers commit hash
```

**To trace back to source:**
```bash
# Extract commit from tag
TAG=v1.1.0-c5abf42
COMMIT=${TAG#*-}  # c5abf42

# Check ai-helpers at that commit
cd ai-helpers
git checkout $COMMIT
cat .claude-plugin/marketplace.json
```

## Version Timeline Example

```
v1.0.0          Initial migration (March 2026)
v1.1.0-c5abf42  First bi-weekly update (April 2, 2026)
v1.1.1-d6ef890  Hotfix for v1.1.0 (April 5, 2026)
v1.2.0-e7f1abc  Second bi-weekly update (April 15, 2026)
v1.3.0-f8g2bcd  Third bi-weekly update (May 1, 2026)
v1.3.1-g9h3cde  Hotfix for v1.3.0 (May 3, 2026)
v2.0.0-h0i4def  Major restructuring (June 2026)
```

## Migration Workflow Integration

### Automated Version Bumping

The migration script (`incremental_migrate_v3.py`) automatically:

1. Reads `gemini-extension.json` version
2. Bumps MINOR version (e.g., 1.0.0 → 1.1.0)
3. Updates `gemini-extension.json`
4. Commits version update
5. Creates tag: `v1.1.0-<commit>`

### Manual Version Override

For hotfixes or MAJOR bumps, manually update before migration:

```bash
# Edit gemini-extension.json
{
  "version": "1.1.1"  # or "2.0.0" for MAJOR
}

# Run migration (will use this version)
python3 incremental_migrate_v3.py
```

## Version Checks

### Check Current Version

```bash
cat gemini-ai-helpers/gemini-extension.json | jq -r .version
```

### Check Latest Tag

```bash
cd gemini-ai-helpers
git describe --tags --abbrev=0
```

### List All Versions

```bash
cd gemini-ai-helpers
git tag -l | sort -V
```

## Version in Reports

Migration reports show version information:

```
=== MIGRATION REPORT ===
Version: v1.1.0-c5abf42
Source:  ai-helpers@c5abf42
Target:  gemini-ai-helpers v1.0.0 → v1.1.0
```

## Best Practices

### DO:
✅ Let migration system auto-bump MINOR for bi-weekly runs
✅ Manually bump PATCH for hotfixes
✅ Include source commit in tag for traceability
✅ Update gemini-extension.json before creating tag
✅ Keep version in sync with git tags

### DON'T:
❌ Skip version bumps for migrations
❌ Reuse version numbers
❌ Create tags without version updates
❌ Mix version schemes (stay semantic)

## Rollback Strategy

### To Previous Version

```bash
cd gemini-ai-helpers
git checkout main

# Find previous tag
git tag -l | sort -V | tail -2

# Rollback
git reset --hard v1.0.0-<commit>
git push origin main --force-with-lease
```

### Restore gemini-extension.json

The version in gemini-extension.json automatically matches the tag when you checkout/reset.

## Summary

**Versioning philosophy:**
- **Semantic:** MAJOR.MINOR.PATCH
- **Traceable:** Include source commit in tag
- **Automated:** Auto-bump MINOR for bi-weekly migrations
- **Consistent:** gemini-extension.json is source of truth

**Current status:**
- Current version: 1.0.0
- Next migration: 1.1.0
- Tag format: v1.1.0-c5abf42

**This ensures clear version history and easy source traceability.**
