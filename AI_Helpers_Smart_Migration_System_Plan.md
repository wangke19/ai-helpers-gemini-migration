# AI Helpers Smart Migration System — Final State

Goal: Migrate Claude Code plugins from `ai-helpers` to the Gemini CLI extension
ecosystem (`gemini-ai-helpers`).

## Status: COMPLETE (33/33 plugins, 130 commands)

## What Was Actually Needed

### Gemini CLI Extension Requirements (learned through trial/error)

1. **`gemini-extension.json`** at repo root — required for `gemini extensions install`
2. **`commands/<namespace>/<command>.toml`** — Gemini CLI only reads `.toml` files,
   not `.md`; uses `FileCommandLoader` from `@google/gemini-cli-core`
3. **TOML literal strings** (`'''`) for `prompt` field — basic strings (`"""`) cause
   parse errors when prompt contains backslash sequences (`\w`, `\d`, `\(`, etc.)

### Installation Command

```
gemini extensions install https://github.com/wangke19/gemini-ai-helpers
```

## Actual Pipeline (as executed)

```
ai-helpers/plugins/
        │
        ▼
 migrate_all.py  (BATCH_SIZE=1 or 2 depending on token load)
   ├── shutil.copytree: copies plugin source to extensions/
   ├── gemini_compat_check.py: scans for Anthropic SDK references
   └── manual sed/python: replaces Claude/Anthropic → Gemini terminology
        │
        ▼
 gemini-ai-helpers/extensions/<plugin>/
   ├── commands/*.md    (source retained)
   ├── skills/          (source retained)
   └── README.md        (updated)
        │
        ▼
 generate_toml.py  (post-migration step — not in original plan)
   ├── Reads extensions/*/commands/*.md
   ├── Extracts description from YAML frontmatter
   ├── Writes commands/<plugin>/<command>.toml using ''' literal strings
   └── Escapes " in description values
        │
        ▼
 gemini-ai-helpers/
   ├── gemini-extension.json
   ├── commands/<plugin>/<command>.toml  (130 files)
   ├── extensions/<plugin>/              (33 plugins)
   └── README.md
```

## What the Original Plan Got Wrong

| Original Assumption | Reality |
|---------------------|---------|
| Commands stay as `.md` files | Gemini CLI only loads `.toml` files |
| `extension.yaml` is the manifest format | `gemini-extension.json` is required |
| `convert_claude_plugin.py` (plugin.json → extension.yaml) needed | No plugin.json existed; not needed |
| `prompt_refactor.py` handles terminology | Done inline with sed/python per-batch |
| Prompts go in `prompt.md` at extension root | Prompts are the `prompt` field in `.toml` files |

## Scripts

| Script | Role | Notes |
|--------|------|-------|
| `migrate_all.py` | Batch orchestrator | BATCH_SIZE tuned per token load |
| `token_estimator.py` | Pre-batch token cost estimator | Prevents quota exhaustion |
| `plugin_usage_ranker.py` | Plugin priority scoring | All scored 0 (no usage data) |
| `gemini_compat_check.py` | Anthropic SDK scanner | Passed on all 33 plugins |
| `convert_claude_plugin.py` | plugin.json converter | Never triggered (no plugin.json) |
| `prompt_refactor.py` | Terminology replacer | Used as reference; done inline |
| `generate_toml.py` | .md → .toml converter | **Critical post-migration step** |
| `validate_toml.py` | TOML parse validator | Catches escape sequence errors |

## Directory Layout (Final)

```
ai-migration-workspace/
├── ai-helpers/               # Source (Claude Code plugins)
├── gemini-ai-helpers/        # Target (Gemini CLI extension)
│   ├── gemini-extension.json
│   ├── README.md
│   ├── LICENSE
│   ├── commands/             # Gemini CLI slash commands (.toml)
│   │   ├── ci/
│   │   ├── jira/
│   │   ├── openshift/
│   │   └── ... (31 namespaces)
│   └── extensions/           # Source plugin files
│       ├── ci/
│       ├── jira/
│       └── ... (33 plugins)
├── migrate_all.py
├── token_estimator.py
├── plugin_usage_ranker.py
├── gemini_compat_check.py
├── convert_claude_plugin.py
├── prompt_refactor.py
├── generate_toml.py          # Added post-migration
├── validate_toml.py          # Added post-migration
├── migration_state.json      # 33/33 completed
└── README.md
```
