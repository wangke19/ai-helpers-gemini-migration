"""
generate_toml.py — Convert .md command files to .toml for Gemini CLI.

Gemini CLI's FileCommandLoader only reads .toml files from commands/.
This script converts all extensions/*/commands/*.md files into the
correct TOML format at commands/<plugin>/<command>.toml.

TOML format:
    description = "Short description"   # optional, from YAML frontmatter
    prompt = '''
    Full prompt body here.
    Backslashes like \\w \\d are safe inside ''' literal strings.
    '''

Usage:
    python3 generate_toml.py
"""

import re
import pathlib

from aihelpers.config import TARGET_DIR as SRC, COMMANDS_DIR as DST


def extract_frontmatter(content):
    """Extract description from YAML frontmatter and return (description, body)."""
    description = ""
    body = content
    fm_match = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
    if fm_match:
        fm = fm_match.group(1)
        desc_match = re.search(r'^description:\s*(.+)$', fm, re.MULTILINE)
        if desc_match:
            description = desc_match.group(1).strip().strip('"\'')
        body = content[fm_match.end():]
    return description, body


def to_toml(description, body):
    """Build a TOML string for a command."""
    lines = []

    if description:
        # Escape backslashes and double-quotes inside the description string
        desc_escaped = description.replace('\\', '\\\\').replace('"', '\\"')
        lines.append(f'description = "{desc_escaped}"')

    # Use TOML literal strings (''' ''') so backslash sequences in the prompt
    # body (\w, \d, \(, etc.) are NOT interpreted as TOML escape sequences.
    # Fall back to basic strings (""") only if body contains '''.
    if "'''" in body:
        body_safe = body.replace('"""', "'''")
        lines.append(f'prompt = """\n{body_safe.rstrip()}\n"""')
    else:
        lines.append(f"prompt = '''\n{body.rstrip()}\n'''")

    return "\n".join(lines) + "\n"


def convert_plugin(plugin_name=None):
    """Convert commands for a specific plugin or all plugins."""
    converted = 0
    errors = []

    # Determine which plugins to process
    if plugin_name:
        plugin_path = SRC / plugin_name / "commands"
        if not plugin_path.exists():
            print(f"No commands directory for plugin: {plugin_name}")
            return
        md_files = sorted(plugin_path.glob("*.md"))
    else:
        md_files = sorted(SRC.rglob("commands/*.md"))
        # Filter to only direct command files
        md_files = [f for f in md_files if f.parent.name == "commands"]

    for md_file in md_files:
        plugin = md_file.parent.parent.name  # e.g. "jira"
        cmd_name = md_file.stem              # e.g. "solve"

        content = md_file.read_text(encoding="utf-8")
        description, body = extract_frontmatter(content)
        toml_content = to_toml(description, body)

        out_dir = DST / plugin
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / f"{cmd_name}.toml"
        out_file.write_text(toml_content, encoding="utf-8")
        converted += 1

    if converted > 0:
        print(f"Converted {converted} .md commands to .toml")
        if errors:
            for e in errors:
                print(f"  ERROR: {e}")
        else:
            print("Run validate_toml.py to confirm all files parse correctly.")
    else:
        print("No commands to convert")


def convert_all():
    """Convert all plugins."""
    convert_plugin(None)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        # Convert specific plugin
        convert_plugin(sys.argv[1])
    else:
        # Convert all
        convert_all()
