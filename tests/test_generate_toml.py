from aihelpers.generate_toml import extract_frontmatter, to_toml


def test_placeholder():
    pass  # TODO: add real tests


def test_extract_frontmatter_with_description():
    content = "---\ndescription: My command\n---\nBody text"
    description, body = extract_frontmatter(content)
    assert description == "My command"
    assert body == "Body text"


def test_extract_frontmatter_without_frontmatter():
    content = "Just body text"
    description, body = extract_frontmatter(content)
    assert description == ""
    assert body == "Just body text"


def test_to_toml_uses_literal_string():
    result = to_toml("", "some prompt body")
    assert "'''" in result
    assert "some prompt body" in result
