from __future__ import annotations

from integrations.notify import format_vacancy_message


def test_format_vacancy_message_is_title_and_url_only() -> None:
    message = format_vacancy_message("Senior iOS Engineer", "https://company.com/jobs/123")
    assert message == "Senior iOS Engineer\nhttps://company.com/jobs/123"


def test_format_vacancy_message_strips_whitespace() -> None:
    message = format_vacancy_message("  Swift Developer  ", "  https://example.com/a  ")
    assert message == "Swift Developer\nhttps://example.com/a"
