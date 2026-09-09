# Collection operations

## Success and partial coverage

A successful workflow means the run completed, not that every company was readable.
Read the `Vacancy collection` step summary and `collect-diagnostics-*` artifact:

- `healthy`: no reported source or delivery failures.
- `degraded`: usable results were processed, but some sources failed or degraded.
- `failed`: total company-source outage, failed CRM writes, failed notification, or incomplete requested sync configuration. A script crash also fails the Actions step; an artifact with `status: collected` is an intermediate checkpoint, not delivery confirmation.

`diagnostics/collect.json` contains source status/reason, response time, raw,
normalized and Inbox-eligible counts, plus rejection categories and duplicate
counts. Counts before grouping are per-source; a role may appear in several
sources. Rejection categories may overlap. No vacancy descriptions, email
contents or credential values are included. Errors redact configured secrets
and URLs. The report is written only when `COLLECT_DIAGNOSTICS_PATH` is set.

An empty Inbox can be valid. Compare source scan counts with normalization
rejections, `ai_details_missing`, geography rejections and existing role history
before treating it as a collector failure. Disabled sources are outside the
run's denominator; the registry coverage audit still needs separate review.

## GitHub access

The existing access was checked read-only on 2026-09-09: Actions were enabled,
the current local GitHub account could read runs/logs, and recent Collect and
liveness runs successfully used CRM access. Secret names were checked, never
values. A later token expiry still requires investigation.

Keep the access boundaries separate:

- Local diagnosis needs repository/Actions read access. It does not require
  running a workflow, changing repository settings or reading secret values.
- CI uses `contents: read` and no delivery secrets for offline verification.
- Collect needs `contents: write` for history and `actions: write` for its
  existing downstream dispatch. Existing workflow permissions are retained.
- Private Project access uses the existing `CAREER_AGENT_TOKEN`; repository
  `GITHUB_TOKEN` permissions do not replace Project authorization. When sync is
  requested but its configuration is incomplete, collection fails before any
  record can be marked as handled locally.

Read-only diagnosis examples:

```bash
gh run list --repo vil4max/ios-hunter --workflow collect.yml --limit 10
gh run view RUN_ID --repo vil4max/ios-hunter --log-failed
gh run view RUN_ID --repo vil4max/ios-hunter --log
gh run download RUN_ID --repo vil4max/ios-hunter --dir /tmp/ios-hunter-run
```

Do not print tokens or use `gh auth token` for diagnostics. Do not dispatch
Collect or liveness as an offline test: they can write CRM and send messages.
Even the current liveness `--dry-run` still invokes its notification function.

## State recovery

Actions uploads `collect-recovery-*` for seven days, including `seen.json`,
source baseline, Telegram cursors and completed collect slots. These files
contain private career metadata; keep artifacts inside the private repository.

Successful partial CRM processing is persisted even when another item fails.
A failed pipeline cannot mark its collect slot complete, and failed CRM sync
cannot advance Telegram cursors. Repeated source/URL absence never erases
history; even explicit closure cleanup preserves applied/dropped/archived
user decisions.

If a state rebase conflicts, the run fails immediately with its recovery
artifact intact. Fetch/push transport races have bounded retries. Recover by
comparing the artifact against the latest remote state; retain user decisions,
monotonic cursors and actually completed slots. Never overwrite the entire
remote state with an old artifact or reset the history to force a re-run.
Existing CRM drafts are looked up by URL and normalized company/title on retry.

## Scheduling and remaining source limits

The schedule targets Kyiv 09/12/15/18. On September 7 and 8, 2026, the recorded
runs filled only two slots each despite the active hourly trigger. The precise
cause is not established; local parser changes cannot guarantee hosted cron
delivery. The existing opt-in Mac launchd backup is documented in README and
has not been installed or modified by this work.

Compare latest Collect, IMAP and liveness execution times with the intended
schedule. IMAP's latest observed execution was September 2 even though Collect
ran later; investigate its downstream trigger separately before claiming full
mail automation health. No trigger was dispatched during this verification.

Latest observed Collect had HTTP 403 for AltexSoft and RBI. Logs make these
coverage gaps visible; they do not bypass site protections. Generic HTML,
pagination limits and title-only AI sources remain coverage constraints.
Liveness treats a generic Careers page or empty HTTP 200 shell without specific
job evidence as unknown/skipped, never as proof of an open vacancy.

## Deterministic verification

Use the existing local `.venv`; do not install dependencies merely for auditing:

```bash
.venv/bin/python -m ruff check .
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider
```

CI also runs the import check in `.github/workflows/ci.yml`. These tests mock
collection, delivery and GitHub. A green local suite validates rules and failure
handling; it does not prove live reachability or deployed workflow behavior.
