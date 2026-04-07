from aihelpers.prompt_refactor import refactor_prompt


def test_placeholder():
    pass  # TODO: add real tests


def test_refactor_prompt_replaces_claude():
    result = refactor_prompt("You are Claude.")
    assert "Claude" not in result
    assert "Gemini" in result


def test_refactor_prompt_strips_xml_tags():
    result = refactor_prompt("<instructions>Do this</instructions>")
    assert "<instructions>" not in result
    assert "Do this" in result


def test_refactor_prompt_empty_string():
    result = refactor_prompt("")
    assert result == ""
