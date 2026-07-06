from __future__ import annotations


def render_named_template(template: str, values: dict[str, str]) -> str:
    result = template
    keys = [key for key in values if key != "description"]
    if "description" in values:
        keys.append("description")
    for key in keys:
        result = result.replace("{" + key + "}", values[key])
    return result
