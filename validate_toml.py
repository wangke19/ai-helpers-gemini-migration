"""
validate_toml.py — Validate all .toml files in commands/ parse correctly.

Uses the same TOML parser (@iarna/toml via node) that Gemini CLI uses
internally in FileCommandLoader, ensuring exact compatibility.

Usage:
    python3 validate_toml.py
"""

import subprocess
import pathlib
import sys

COMMANDS_DIR = pathlib.Path("gemini-ai-helpers/commands")
TOML_PARSER = "/usr/local/lib/node_modules/@google/gemini-cli/node_modules/@iarna/toml"


def validate_with_node():
    """Validate using the exact same TOML parser Gemini CLI uses."""
    toml_files = sorted(COMMANDS_DIR.rglob("*.toml"))
    if not toml_files:
        print("No .toml files found in", COMMANDS_DIR)
        sys.exit(1)

    # Build a node script that parses every file and reports errors
    files_json = "[" + ",".join(f'"{f}"' for f in toml_files) + "]"
    node_script = f"""
const toml = require('{TOML_PARSER}');
const fs = require('fs');
const files = {files_json};
let ok = 0, fail = 0;
for (const f of files) {{
  try {{
    const content = fs.readFileSync(f, 'utf8');
    const parsed = toml.parse(content);
    if (!parsed.prompt) {{
      console.log('WARN (no prompt):', f);
    }}
    ok++;
  }} catch(e) {{
    console.log('FAIL:', f, '->', e.message.split('\\n')[0]);
    fail++;
  }}
}}
console.log(`\\nResult: ${{ok}} OK, ${{fail}} FAILED out of ${{files.length}} files`);
process.exit(fail > 0 ? 1 : 0);
"""

    result = subprocess.run(
        ["node", "-e", node_script],
        capture_output=True, text=True
    )
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.returncode


def validate_with_python():
    """Fallback: validate using Python's tomllib (Python 3.11+) or tomli."""
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore
        except ImportError:
            print("Neither tomllib (Python 3.11+) nor tomli available.")
            print("Install tomli: pip install tomli")
            return 1

    toml_files = sorted(COMMANDS_DIR.rglob("*.toml"))
    ok, fail = 0, 0
    for f in toml_files:
        try:
            with open(f, "rb") as fh:
                data = tomllib.load(fh)
            if "prompt" not in data:
                print(f"WARN (no prompt): {f}")
            ok += 1
        except Exception as e:
            print(f"FAIL: {f} -> {e}")
            fail += 1

    print(f"\nResult: {ok} OK, {fail} FAILED out of {len(toml_files)} files")
    return 1 if fail > 0 else 0


if __name__ == "__main__":
    # Try node (exact Gemini CLI parser) first, fall back to Python
    try:
        subprocess.run(["node", "--version"], capture_output=True, check=True)
        sys.exit(validate_with_node())
    except (subprocess.CalledProcessError, FileNotFoundError):
        sys.exit(validate_with_python())
