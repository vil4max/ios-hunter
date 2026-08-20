from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from integrations.vacancy_probe import ProbeResult, probe_vacancy_url
from planner.plan import ProjectCard
from project_sync.github_client import GitHubClient, GitHubGraphQLError, ProjectMeta

PACKAGE_START = "<!-- application-package:start -->"
PACKAGE_END = "<!-- application-package:end -->"


@dataclass(frozen=True)
class ApplicationPackage:
    resume: str
    message: str = ""
    answers: tuple[str, ...] = ()


def build_application_package_body(
    body: str,
    package: ApplicationPackage,
    *,
    prepared_at: date | None = None,
) -> str:
    stamp = prepared_at or date.today()
    lines = [
        PACKAGE_START,
        "## Application package",
        "",
        f"- Prepared: {stamp.isoformat()}",
        f"- CV: {package.resume}",
        f"- Message: {package.message or 'Not required'}",
    ]
    if package.answers:
        lines.extend(["- Screening answers:", *[f"  - {answer}" for answer in package.answers]])
    lines.extend(["- Submission: owner approval required", PACKAGE_END])
    section = "\n".join(lines)
    text = (body or "").rstrip()
    start = text.find(PACKAGE_START)
    end = text.find(PACKAGE_END)
    if start >= 0 and end >= start:
        end += len(PACKAGE_END)
        return f"{text[:start].rstrip()}\n\n{section}{text[end:]}".rstrip() + "\n"
    return f"{text}\n\n{section}\n" if text else f"{section}\n"


def prepare_application(
    client: GitHubClient,
    meta: ProjectMeta,
    card: ProjectCard,
    package: ApplicationPackage,
    *,
    probe=probe_vacancy_url,
    prepared_at: date | None = None,
) -> ProbeResult:
    if not package.resume.strip():
        raise ValueError("resume label is required")
    url = (card.url or card.canonical_url).strip()
    result = probe(url, card_title=card.title)
    if result.skipped:
        raise RuntimeError(f"vacancy could not be verified: {result.reason}")
    if result.closed:
        raise RuntimeError(f"vacancy is closed: {result.reason}")
    draft_id = client.draft_issue_id_for_item(meta.project_id, card.item_id)
    if not draft_id:
        raise GitHubGraphQLError("Project card is not an editable draft issue")
    client.update_draft_issue(
        draft_id,
        body=build_application_package_body(card.body, package, prepared_at=prepared_at),
    )
    return result
