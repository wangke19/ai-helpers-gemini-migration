# AI Helpers Gemini Migration

Tooling to migrate plugins from [`ai-helpers`](https://github.com/openshift-eng/ai-helpers) (Claude Code) to [`gemini-ai-helpers`](https://github.com/wangke19/gemini-ai-helpers) (Gemini CLI).

One command pulls the latest `ai-helpers`, detects changes, migrates all updated plugins, and opens a GitHub PR.

## Quick Start

### Prerequisites

- Python 3.9+
- [`gh`](https://cli.github.com/) CLI authenticated (`gh auth status`)
- Both repos cloned locally and symlinked:

```bash
ln -s /path/to/ai-helpers ai-helpers
ln -s /path/to/gemini-ai-helpers gemini-ai-helpers
```

### Install dev dependencies

```bash
pip install -e ".[dev]"
```

### Run migration

```bash
python3 -m aihelpers.incremental_migrate
```

This single command:
1. Pulls latest `ai-helpers`
2. Detects new/updated plugins
3. Migrates each plugin (replaces Claude/Anthropic references, regenerates `.toml` commands)
4. Commits per-plugin changes to a migration branch
5. Bumps the version in `gemini-extension.json` and creates a git tag
6. Pushes the branch and opens a PR on `gemini-ai-helpers`

## Project Structure

```
ai-helpers-gemini-migration/
├── aihelpers/                      # Python package
│   ├── incremental_migrate.py      # Main entry point — full pipeline
│   ├── detect_changes.py           # MD5-based change detection
│   ├── generate_toml.py            # .md → .toml converter for Gemini CLI
│   ├── validate_toml.py            # TOML parse validation
│   ├── prompt_refactor.py          # Claude→Gemini text substitution
│   ├── gemini_compat_check.py      # Scan for remaining Anthropic references
│   ├── generate_migration_report.py
│   ├── migration_summary.py
│   ├── plugin_usage_ranker.py
│   ├── token_estimator.py
│   ├── migrate_all.py
│   └── convert_claude_plugin.py
├── tests/
│   ├── test_detect_changes.py
│   ├── test_generate_toml.py
│   └── test_prompt_refactor.py
├── pyproject.toml
├── scheduled_migration.sh       # Cron-friendly wrapper
├── migration_state.json         # Runtime state (gitignored dirs)
└── migration_changes.json          # Last change detection output
```

## Individual Commands

```bash
# Detect what needs migration (writes migration_changes.json)
python3 -m aihelpers.detect_changes

# Regenerate .toml commands from .md sources (all plugins)
python3 -m aihelpers.generate_toml

# Validate all .toml files parse correctly
python3 -m aihelpers.validate_toml

# Print migration summary
python3 -m aihelpers.migration_summary

# Run tests
python3 -m pytest tests/ -v
```

## Gemini CLI Extension Format

Each slash command is a `.toml` file under `commands/<namespace>/<command>.toml`:

```toml
description = "Short description shown in the command picker"
prompt = '''
Full prompt body here.
Backslashes are safe (\w \d \() because ''' is a TOML literal string.
'''
```

- Use `'''` (literal string), not `"""` — avoids TOML interpreting `\w`, `\d`, etc.
- File `commands/jira/solve.toml` → slash command `/jira:solve`

## Architecture

```
ai-helpers/plugins/         Source: Claude Code plugin .md commands
        │
        ▼
incremental_migrate.py      git pull → detect changes → copy + clean references
        │
        ▼
gemini-ai-helpers/
  extensions/*/             Gemini-cleaned .md sources
  commands/*/*.toml         Generated TOML commands for Gemini CLI
  gemini-extension.json     Extension manifest (version auto-bumped)
        │
        ▼
GitHub PR                   Branch pushed, PR opened via gh CLI
```

## Scheduled Automation

To run bi-weekly via cron:

```
0 0 1,15 * * /path/to/scheduled_migration.sh
```
