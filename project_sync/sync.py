from __future__ import annotations

from dataclasses import dataclass, field

from config.settings import Settings
from parser.normalize import Vacancy, canonicalize_url
from project_sync.github_client import GitHubClient, GitHubGraphQLError, ProjectMeta


CANONICAL_MARKER_PREFIX = "Canonical-URL: "


@dataclass
class SyncItemResult:
    canonical_url: str
    company: str
    title: str
    issue_number: int | None = None
    issue_url: str = ""
    item_id: str = ""
    created: bool = False
    existing: bool = False
    failed: bool = False
    error: str = ""


@dataclass
class SyncResult:
    created: list[SyncItemResult] = field(default_factory=list)
    existing: list[SyncItemResult] = field(default_factory=list)
    failed: list[SyncItemResult] = field(default_factory=list)
    skipped_disabled: bool = False

    @property
    def created_count(self) -> int:
        return len(self.created)

    @property
    def existing_count(self) -> int:
        return len(self.existing)

    @property
    def failed_count(self) -> int:
        return len(self.failed)


def build_issue_body(vacancy: Vacancy) -> str:
    canonical = vacancy.canonical_url or canonicalize_url(vacancy.url)
    lines = [
        "<!-- career-agent -->",
        f"{CANONICAL_MARKER_PREFIX}{canonical}",
        "",
        f"**Company:** {vacancy.company}",
        f"**Title:** {vacancy.title}",
        f"**Source:** {vacancy.source}",
        f"**URL:** {vacancy.url}",
    ]
    if vacancy.location:
        lines.append(f"**Location:** {vacancy.location}")
    if vacancy.remote:
        lines.append(f"**Remote:** {vacancy.remote}")
    return "\n".join(lines) + "\n"


def build_issue_title(vacancy: Vacancy) -> str:
    return f"{vacancy.company} — {vacancy.title}"


def _apply_project_fields(
    client: GitHubClient,
    meta: ProjectMeta,
    item_id: str,
    vacancy: Vacancy,
    *,
    status_name: str,
) -> None:
    if meta.status_field:
        option_id = meta.status_field.options.get(status_name)
        if option_id:
            client.set_single_select_field(
                project_id=meta.project_id,
                item_id=item_id,
                field_id=meta.status_field.id,
                option_id=option_id,
            )

    text_values = {
        "URL": vacancy.url,
        "Company": vacancy.company,
        "Source": vacancy.source,
        "Canonical URL": vacancy.canonical_url or canonicalize_url(vacancy.url),
    }
    for field_name, value in text_values.items():
        project_field = meta.fields_by_name.get(field_name)
        if project_field and value:
            client.set_text_field(
                project_id=meta.project_id,
                item_id=item_id,
                field_id=project_field.id,
                text=value[:1024],
            )


class ProjectSync:
    """Sync vacancies as private Project draft items (never public repo Issues)."""

    def __init__(self, settings: Settings, client: GitHubClient | None = None) -> None:
        self._settings = settings
        self._client = client or GitHubClient(settings.github_token)
        self._meta: ProjectMeta | None = None

    def _ensure_meta(self) -> ProjectMeta:
        if self._meta is None:
            self._meta = self._client.resolve_project(
                self._settings.project_owner,
                self._settings.project_number,
            )
        return self._meta

    def sync_vacancy(self, vacancy: Vacancy, *, status_name: str = "Inbox") -> SyncItemResult:
        canonical = vacancy.canonical_url or canonicalize_url(vacancy.url)
        base = SyncItemResult(
            canonical_url=canonical,
            company=vacancy.company,
            title=vacancy.title,
        )
        if not canonical:
            base.failed = True
            base.error = "missing canonical URL"
            return base

        try:
            meta = self._ensure_meta()
            existing_item_id = self._client.find_project_item_by_canonical_url(
                meta.project_id,
                canonical,
            )
            if existing_item_id is not None:
                base.existing = True
                base.item_id = existing_item_id
                return base

            item_id = self._client.add_draft_issue(
                meta.project_id,
                title=build_issue_title(vacancy),
                body=build_issue_body(vacancy),
            )
            _apply_project_fields(self._client, meta, item_id, vacancy, status_name=status_name)
            base.created = True
            base.item_id = item_id
            return base
        except (GitHubGraphQLError, OSError, ValueError) as error:
            base.failed = True
            base.error = str(error)
            return base

    def sync_vacancies(
        self,
        vacancies: list[Vacancy],
        *,
        status_name: str = "Inbox",
    ) -> SyncResult:
        if not self._settings.configured_for_sync:
            return SyncResult(skipped_disabled=True)

        result = SyncResult()
        for vacancy in vacancies:
            item = self.sync_vacancy(vacancy, status_name=status_name)
            if item.created:
                result.created.append(item)
            elif item.existing:
                result.existing.append(item)
            else:
                result.failed.append(item)
        return result

    def seed_archived(self, vacancies: list[Vacancy]) -> SyncResult:
        return self.sync_vacancies(vacancies, status_name="Archived")
