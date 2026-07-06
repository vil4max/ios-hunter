from integrations.template_render import render_named_template


def test_render_named_template_ignores_braces_in_values() -> None:
    template = "Company: {company}\nBody:\n{description}"
    rendered = render_named_template(
        template,
        {
            "company": "Acme",
            "description": "Use {company} in Swift {title}",
        },
    )
    assert "Use {company} in Swift {title}" in rendered
    assert rendered.startswith("Company: Acme")
