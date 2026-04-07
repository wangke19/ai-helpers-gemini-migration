# Python Project Refactor Design

**Date:** 2026-04-08  
**Scope:** Restructure flat Python scripts into a standard Python package layout  
**Status:** Approved

---

## Problem

All 13 Python scripts live flat at the repo root alongside state files, shell scripts, and docs. There is no package structure, no `pyproject.toml`, no dependency declaration, and no test directory. Intra-script imports are bare (`from plugin_usage_ranker import ...`) and break if invoked from a different working directory.

---

## Goals

- Move all Python scripts into an `aihelpers/` package
- Add `pyproject.toml` with setuptools backend
- Fix all intra-package imports to use `aihelpers.*`
- Add `tests/` directory with stubs for the three most testable modules
- Update shell scripts to use `python3 -m aihelpers.<module>`
- No new functionality, no third-party dependencies added

---

## File Layout

```
ai-helpers-gemini-migration/
├── pyproject.toml
├── .gitignore                      # add .venv/, dist/, *.egg-info/
├── README.md                       # update usage examples
├── aihelpers/
│   ├── __init__.py
│   ├── convert_claude_plugin.py
│   ├── detect_changes.py
│   ├── gemini_compat_check.py
│   ├── generate_migration_report.py
│   ├── generate_toml.py
│   ├── get_marketplace_version.py
│   ├── incremental_migrate_v3.py
│   ├── migrate_all.py
│   ├── migration_summary.py
│   ├── plugin_usage_ranker.py
│   ├── prompt_refactor.py
│   ├── token_estimator.py
│   └── validate_toml.py
├── tests/
│   ├── __init__.py
│   ├── test_detect_changes.py
│   ├── test_generate_toml.py
│   └── test_prompt_refactor.py
├── scheduled_migration_v3.sh
├── test_migration_system.sh
├── migration_state_v2.json         # runtime data, stays at root
└── migration_changes.json          # runtime data, stays at root
```

---

## `pyproject.toml`

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "ai-helpers-gemini-migration"
version = "2.2.0"
description = "Migration tooling from ai-helpers (Claude Code) to gemini-ai-helpers (Gemini CLI)"
requires-python = ">=3.9"
dependencies = []

[tool.setuptools.packages.find]
where = ["."]
include = ["aihelpers*"]

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.ruff]
line-length = 100
```

All dependencies are stdlib-only (`os`, `re`, `json`, `shutil`, `subprocess`, `pathlib`, `hashlib`, `datetime`). No third-party packages required.

---

## Import Changes

All bare intra-package imports updated to absolute package imports:

```python
# Before
from plugin_usage_ranker import rank_plugins
from convert_claude_plugin import convert_plugin

# After
from aihelpers.plugin_usage_ranker import rank_plugins
from aihelpers.convert_claude_plugin import convert_plugin
```

All scripts that serve as entry points already have `if __name__ == "__main__":` guards — these are verified but not changed.

---

## Shell Script Updates

```bash
# Before
python3 incremental_migrate_v3.py

# After
python3 -m aihelpers.incremental_migrate_v3
```

Rationale: `-m` invocation ensures the project root is on `sys.path`, making package imports resolve correctly regardless of the caller's working directory.

---

## Test Stubs

Three modules chosen for initial test stubs based on having pure functions with clear inputs/outputs:

- `tests/test_detect_changes.py` — tests for `clean_claude_references()`
- `tests/test_generate_toml.py` — tests for TOML generation logic
- `tests/test_prompt_refactor.py` — tests for prompt text substitution

Each stub imports the module and contains a `test_placeholder` function. No test logic is implemented — the structure is ready for future test authoring.

---

## Out of Scope

- No new features
- No third-party dependencies
- No CLI entry points (`pip install` won't add shell commands)
- No changes to state file formats or migration logic
- No changes to shell script logic beyond the invocation line
