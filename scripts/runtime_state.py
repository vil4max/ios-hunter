"""Publish allowlisted runtime JSON without rebasing the running checkout."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile

PATHS = frozenset({
    "database/seen.json", "database/email_seen.json", "database/source_baseline.json",
    "database/telegram_cursors.json", "database/collect_slots.json",
    "database/daily_email_days.json",
})
HISTORY = {"database/seen.json", "database/email_seen.json"}
MISSING = object()


class StateConflict(ValueError):
    pass


def merge_state(base, local, remote, path: str, keys: tuple[str, ...] = ()):
    """Merge independent edits; never silently choose between conflicting decisions."""
    values = [v for v in (base, local, remote) if v is not MISSING]
    if path == "database/telegram_cursors.json" and len(keys) == 1:
        if not all(type(v) is int and v >= 0 for v in values):
            raise StateConflict(f"Invalid cursor: {path}")
        return max(values)
    if ((path == "database/daily_email_days.json" and keys == ("days",)) or
            (path == "database/collect_slots.json" and len(keys) == 3 and keys[-1] == "slots")):
        if not all(isinstance(v, list) for v in values):
            raise StateConflict(f"Invalid claim list: {path}")
        items = [item for value in values for item in value]
        expected_type = str if path.endswith("daily_email_days.json") else int
        if not all(type(item) is expected_type for item in items):
            raise StateConflict(f"Invalid claim value: {path}")
        return sorted(set(items))
    if all(isinstance(v, dict) for v in values):
        result = {}
        for key in sorted(set().union(*(v.keys() for v in values))):
            before, ours, theirs = (v.get(key, MISSING) if isinstance(v, dict) else MISSING for v in (base, local, remote))
            # Mail/decision history is append-only at the record level, even after pruning.
            if path in HISTORY and not keys:
                ours = before if ours is MISSING and before is not MISSING else ours
                theirs = before if theirs is MISSING and before is not MISSING else theirs
            merged = merge_state(before, ours, theirs, path, (*keys, key))
            if merged is not MISSING:
                result[key] = merged
        return result
    if local == remote:
        return local
    if local == base:
        return remote
    if remote == base:
        return local
    # Do not include keys/values: email identifiers and career decisions are private.
    raise StateConflict(f"Concurrent field conflict in {path} (depth {len(keys)})")


def git(root: Path, *args: str, data: bytes | None = None, env=None) -> bytes:
    return subprocess.run(["git", *args], cwd=root, input=data, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, check=True, env=env).stdout


def fetch(root: Path) -> str:
    git(root, "fetch", "origin", "refs/heads/main")
    return git(root, "rev-parse", "FETCH_HEAD").decode().strip()


def read_state(root: Path, revision: str, path: str):
    entry = git(root, "ls-tree", revision, "--", path)
    if not entry:
        return {}
    value = json.loads(git(root, "show", f"{revision}:{path}"))
    if not isinstance(value, dict):
        raise StateConflict(f"Expected JSON object: {path}")
    return value


def encode(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def validate_paths(paths):
    if not paths or not set(paths) <= PATHS:
        raise ValueError("Only allowlisted runtime paths can be refreshed or published")


def refresh(root: Path, paths: list[str], snapshot: Path) -> str:
    validate_paths(paths)
    revision = fetch(root)
    # Validate the whole batch before replacing any state. Source code stays pinned.
    states = {path: read_state(root, revision, path) for path in paths}
    for path, state in states.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(encode(state))
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    snapshot.write_bytes(encode({"base": revision, "paths": paths}))
    return revision


def publish(root: Path, snapshot: Path, message: str, attempts: int = 5) -> str | None:
    metadata = json.loads(snapshot.read_bytes())
    paths = metadata["paths"]
    validate_paths(paths)
    base = {path: read_state(root, metadata["base"], path) for path in paths}
    local = {path: json.loads((root / path).read_bytes()) for path in paths}
    if not all(isinstance(value, dict) for value in local.values()):
        raise StateConflict("Runtime state must contain JSON objects")
    remote_revision = fetch(root)
    for _ in range(attempts):
        remote = {path: read_state(root, remote_revision, path) for path in paths}
        merged = {path: merge_state(base[path], local[path], remote[path], path) for path in paths}
        changed = {path: state for path, state in merged.items() if state != remote[path]}
        if not changed:
            return None
        with tempfile.TemporaryDirectory(prefix="career-state-") as temp:
            env = dict(os.environ, GIT_INDEX_FILE=str(Path(temp) / "index"),
                       GIT_AUTHOR_NAME="github-actions[bot]", GIT_COMMITTER_NAME="github-actions[bot]",
                       GIT_AUTHOR_EMAIL="41898282+github-actions[bot]@users.noreply.github.com",
                       GIT_COMMITTER_EMAIL="41898282+github-actions[bot]@users.noreply.github.com")
            git(root, "read-tree", remote_revision, env=env)
            for path, state in changed.items():
                blob = git(root, "hash-object", "-w", "--stdin", data=encode(state)).decode().strip()
                git(root, "update-index", "--add", "--cacheinfo", "100644", blob, path, env=env)
            tree = git(root, "write-tree", env=env).decode().strip()
            revision = git(root, "commit-tree", tree, "-p", remote_revision, "-m", message, env=env).decode().strip()
        try:
            git(root, "push", "origin", f"{revision}:refs/heads/main")
            return revision
        except subprocess.CalledProcessError:
            latest = fetch(root)
            if latest == remote_revision:
                raise
            remote_revision = latest
    raise StateConflict("Runtime state push races exhausted; recover from the workflow artifact")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("refresh", "publish"))
    parser.add_argument("paths", nargs="*")
    parser.add_argument("--snapshot", type=Path, default=Path("diagnostics/runtime-state-base.json"))
    parser.add_argument("--message", default="chore(state): persist runtime state [skip ci]")
    args = parser.parse_args()
    try:
        if args.action == "refresh":
            print("Runtime state refreshed:", refresh(Path.cwd(), args.paths, args.snapshot))
        else:
            print("Runtime state published:", publish(Path.cwd(), args.snapshot, args.message) or "unchanged")
    except (StateConflict, ValueError, OSError, subprocess.CalledProcessError) as error:
        # Avoid echoing subprocess arguments/output or JSON data from private state.
        detail = str(error) if isinstance(error, StateConflict) else type(error).__name__
        report = Path("diagnostics/runtime-state-error.json")
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_bytes(encode({"action": args.action, "error": detail, "recovery": "Use the state recovery artifact"}))
        print(f"Runtime state {args.action} failed: {detail}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
