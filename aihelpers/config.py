"""
Central path configuration for ai-helpers-gemini-migration.

Priority (high → low):
  1. Environment variables: AI_HELPERS_DIR, GEMINI_REPO_DIR
  2. migration.conf in project root
  3. Error (no silent fallback)

Run setup.sh once to clone repos and generate migration.conf.
"""

import os
import configparser
import sys
from pathlib import Path

# Project root = parent of this file's directory (aihelpers/)
PROJECT_ROOT = Path(__file__).parent.parent


def _load_conf() -> dict:
    conf_file = PROJECT_ROOT / "migration.conf"
    if not conf_file.exists():
        return {}
    conf = configparser.ConfigParser()
    conf.read(conf_file)
    if conf.has_section("repos"):
        return dict(conf["repos"])
    return {}


def _resolve(env_var: str, conf_key: str, conf: dict) -> Path:
    raw = os.getenv(env_var) or conf.get(conf_key)
    if not raw:
        print(
            f"ERROR: {env_var} not set and '{conf_key}' missing from migration.conf.\n"
            f"Run ./setup.sh to configure repo paths.",
            file=sys.stderr,
        )
        sys.exit(1)
    path = Path(raw)
    if not path.exists():
        print(
            f"ERROR: {env_var} path does not exist: {path}\n"
            f"Check migration.conf or re-run ./setup.sh.",
            file=sys.stderr,
        )
        sys.exit(1)
    return path


_conf = _load_conf()

AI_HELPERS_REPO  = _resolve("AI_HELPERS_DIR",  "ai_helpers_dir",  _conf)
GEMINI_REPO      = _resolve("GEMINI_REPO_DIR", "gemini_repo_dir", _conf)

SOURCE_DIR    = AI_HELPERS_REPO / "plugins"
SOURCE_REPO   = AI_HELPERS_REPO
TARGET_DIR    = GEMINI_REPO / "extensions"
COMMANDS_DIR  = GEMINI_REPO / "commands"
