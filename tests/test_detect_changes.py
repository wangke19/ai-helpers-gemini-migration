from aihelpers.detect_changes import clean_claude_references


def test_placeholder():
    pass  # TODO: add real tests


def test_clean_claude_references_replaces_claude_code():
    result = clean_claude_references("Use Claude Code to run this")
    assert "Claude Code" not in result


def test_clean_claude_references_replaces_anthropic():
    result = clean_claude_references("Anthropic API key required")
    assert "Anthropic" not in result
