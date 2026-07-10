from __future__ import annotations

from integrations.telegram import send_message
from parser.normalize import Vacancy


def format_vacancy_message(title: str, url: str) -> str:
    return f"{title.strip()}\n{url.strip()}"


def notify_vacancy(vacancy: Vacancy) -> None:
    send_message(format_vacancy_message(vacancy.title, vacancy.url))
