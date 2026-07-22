from __future__ import annotations

import os
from dataclasses import dataclass


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


STATUS_WORKFLOW: tuple[str, ...] = (
    "Inbox",
    "Applied",
    "Replied",
    "Screening",
    "Post-Screen",
    "Technical",
    "Post-Tech",
    "Archived",
)

ACTIVE_PIPELINE_STATUSES: frozenset[str] = frozenset(
    {
        "Inbox",
        "Applied",
        "Replied",
        "Screening",
        "Post-Screen",
        "Technical",
        "Post-Tech",
    }
)

STALE_STATUSES: frozenset[str] = frozenset(
    {
        "Applied",
        "Replied",
        "Screening",
        "Post-Screen",
        "Technical",
        "Post-Tech",
    }
)

CLOSE_REASON_OPTIONS: tuple[str, ...] = (
    "No reply",
    "Rejected HR",
    "Rejected tech",
    "Accepted offer",
    "Declined offer",
    "Duplicate",
    "Not interested",
    "Withdrawn",
    "Role closed",
    "Other",
)

CLOSED_STAGE_OPTIONS: tuple[str, ...] = (
    "Inbox",
    "Applied",
    "Replied",
    "Screening",
    "Post-Screen",
    "Technical",
    "Post-Tech",
    "Offer",
)

CHANNEL_OPTIONS: tuple[str, ...] = (
    "Djinni",
    "LinkedIn",
    "Telegram",
    "Company site",
    "Recruiter",
    "Other",
)


@dataclass(frozen=True)
class Settings:
    github_token: str
    github_repository: str
    project_owner: str
    project_number: int
    project_board_url: str
    sync_enabled: bool
    seen_gate_enabled: bool
    stale_days: int
    inbox_new_days: int
    research_stale_days: int

    @property
    def repo_owner(self) -> str:
        return self.github_repository.split("/", 1)[0]

    @property
    def repo_name(self) -> str:
        parts = self.github_repository.split("/", 1)
        return parts[1] if len(parts) == 2 else ""

    @property
    def configured_for_sync(self) -> bool:
        return bool(
            self.sync_enabled
            and self.github_token
            and self.github_repository
            and self.project_owner
            and self.project_number > 0
        )


def load_settings() -> Settings:
    repository = os.environ.get("GITHUB_REPOSITORY", "").strip()
    return Settings(
        github_token=os.environ.get("CAREER_AGENT_TOKEN", "").strip()
        or os.environ.get("GITHUB_TOKEN", "").strip(),
        github_repository=repository,
        project_owner=(
            os.environ.get("CAREER_PROJECT_OWNER", "").strip()
            or os.environ.get("GITHUB_PROJECT_OWNER", "").strip()
        ),
        project_number=_env_int("CAREER_PROJECT_NUMBER", _env_int("GITHUB_PROJECT_NUMBER", 0)),
        project_board_url=os.environ.get("PROJECT_BOARD_URL", "").strip(),
        sync_enabled=_env_bool("CAREER_AGENT_SYNC_ENABLED", default=False),
        seen_gate_enabled=_env_bool("CAREER_AGENT_SEEN_GATE", default=True),
        stale_days=_env_int("CAREER_AGENT_STALE_DAYS", 7),
        inbox_new_days=_env_int("CAREER_AGENT_INBOX_NEW_DAYS", 2),
        research_stale_days=_env_int("CAREER_AGENT_RESEARCH_STALE_DAYS", 5),
    )
