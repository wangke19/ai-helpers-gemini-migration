# AI Helpers Migration System v2.2

**From `ai-helpers` (Claude Code) to `gemini-ai-helpers` (Gemini CLI)**

Automated bi-weekly migration system with semantic versioning, branch-based workflow, approval gates, and comprehensive testing.

## 🚀 Quick Start

```bash
# Detect changes
python3 -m aihelpers.detect_changes

# Run migration
python3 -m aihelpers.incremental_migrate

# Or run scheduled (bi-weekly automation)
./scheduled_migration_v3.sh
```

See [QUICKSTART.md](QUICKSTART.md) for detailed usage.

## 📚 Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - Get started in 5 minutes
- **[BRANCHING_STRATEGY.md](BRANCHING_STRATEGY.md)** - Branch and tag workflow
- **[MIGRATION_V2_PLAN.md](MIGRATION_V2_PLAN.md)** - Complete system design
- **[AI_Helpers_Smart_Migration_System_Plan.md](AI_Helpers_Smart_Migration_System_Plan.md)** - v1.0 history

## What's New in v2.1

- ✅ **Branch-based workflow** - Isolated migration branch, clean main
- ✅ **Tag-based versioning** - Main always points to latest tag
- ✅ **Incremental migration** - Only migrate updated/new plugins
- ✅ **Change detection** - MD5 hash-based comparison
- ✅ **Automated testing** - Sanity tests before commit
- ✅ **Scheduled automation** - Bi-weekly cron job
- ✅ **One commit per plugin** - Atomic, reviewable changes
- ✅ **Easy rollback** - Reset main to previous tag
- ✅ **Migration history** - Track all migrations in state file

## Current Status

**Source:** 34 plugins (ai-helpers)  
**Target:** 33 plugins (gemini-ai-helpers)  
**Need migration:** 30 plugins (2 new, 28 updated)

See `migration_changes.json` for details.

## v1.0 Migration Results (Historical)

The initial migration (v1.0) successfully migrated all 33 plugins. See below for what was learned.

## What Was Learned (v1.0)

### Gemini CLI Extension Structure

A valid Gemini CLI extension requires:

```
<repo-root>/
├── gemini-extension.json        # Required manifest (name, version, description)
├── commands/
│   └── <namespace>/
│       └── <command>.toml       # One .toml per command (NOT .md)
├── extensions/                  # Source plugin files (retained for reference)
│   └── <plugin>/
│       └── commands/*.md
└── README.md
```

### gemini-extension.json

Minimal required manifest at the repo root:

```json
{
  "name": "gemini-ai-helpers",
  "version": "1.0.0",
  "description": "..."
}
```

### Command .toml Format

Each slash command is a `.toml` file under `commands/<namespace>/<command>.toml`:

```toml
description = "Short description shown in the command picker"
prompt = '''
Full command prompt body here.
Backslashes are safe (\w \d \( etc.) because ''' is a TOML literal string.
'''
```

Key rules:
- Use `'''` (literal string) **not** `"""` (basic string) for `prompt` — avoids
  TOML interpreting backslash sequences like `\w`, `\d`, `\(` as escape chars
- Escape `"` inside `description` as `\"`
- File path `commands/jira/solve.toml` maps to slash command `/jira:solve`

### Installation

```
gemini extensions install https://github.com/wangke19/gemini-ai-helpers
```

Or via SSH (if local git config rewrites HTTPS to SSH):

```
gemini extensions install git@github.com:wangke19/gemini-ai-helpers
```

### Updating

```
gemini extensions update gemini-ai-helpers
```

## Pipeline Scripts

| Script | Purpose | Status |
|--------|---------|--------|
| `migrate_all.py` | Orchestrates batched migration, maintains state | ✅ Done (33/33) |
| `token_estimator.py` | Estimates token cost before each batch | ✅ Done |
| `plugin_usage_ranker.py` | Ranks plugins by priority | ✅ Done |
| `convert_claude_plugin.py` | Converts plugin.json schema (unused — no plugin.json existed) | N/A |
| `prompt_refactor.py` | Rewrites Claude-specific terminology | ✅ Done (via sed/python inline) |
| `gemini_compat_check.py` | Scans for Anthropic SDK references | ✅ Done |
| `generate_toml.py` | **NEW** — Converts .md commands to .toml for Gemini CLI | ✅ Done |

## generate_toml.py

Run this after any changes to `extensions/*/commands/*.md` to regenerate
the `.toml` files that Gemini CLI actually loads:

```bash
python3 -m aihelpers.generate_toml
```

Then validate all `.toml` files parse correctly:

```bash
python3 -m aihelpers.validate_toml
```

## Architecture

```
[ai-helpers/plugins/]           Source: Claude Code plugin .md commands
        │
        ▼
 migrate_all.py                 Copy + clean Claude/Anthropic references
        │
        ▼
 extensions/*/commands/*.md     Gemini-cleaned source (retained)
        │
        ▼
 generate_toml.py               Convert .md → .toml (Gemini CLI format)
        │
        ▼
 commands/<ns>/<cmd>.toml       Gemini CLI slash commands (/ns:cmd)
        │
        ▼
 gemini-extension.json          Extension manifest
        │
        ▼
 gemini extensions install      Installs to ~/.gemini/extensions/
```

## Migration Results

- **33/33 plugins** migrated from `ai-helpers` → `gemini-ai-helpers`
- **130 slash commands** converted from `.md` → `.toml`
- **0 TOML parse errors** after switching to literal strings (`'''`)
- All Claude/Anthropic references replaced with Gemini equivalents
- Env vars renamed: `CLAUDE_PLUGIN_ROOT` → `GEMINI_EXTENSION_ROOT`, etc.
