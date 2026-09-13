from __future__ import annotations

import json
import subprocess

import pytest

from scripts import runtime_state as state

SEEN = "database/seen.json"
CURSOR = "database/telegram_cursors.json"


def git(root, *args):
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True).stdout.strip()


def write(root, path, value):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value))


def commit(root, message="test: change"):
    git(root, "add", ".")
    git(root, "commit", "-m", message)
    git(root, "push", "origin", "main")


def isolate_git(tmp_path, monkeypatch):
    # Fixture repositories must not inherit the owner's hooks or an enclosing push's repository.
    for name in git(tmp_path, "rev-parse", "--local-env-vars").splitlines():
        monkeypatch.delenv(name, raising=False)
    config = tmp_path / "gitconfig"
    config.write_text("")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(config))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")


@pytest.fixture
def repos(tmp_path, monkeypatch):
    isolate_git(tmp_path, monkeypatch)
    remote = tmp_path / "remote.git"
    remote.mkdir()
    git(remote, "init", "--bare", "--initial-branch=main")
    work = tmp_path / "work"
    git(tmp_path, "clone", str(remote), str(work))
    git(work, "config", "user.name", "Test")
    git(work, "config", "user.email", "test@example.invalid")
    write(work, SEEN, {"old": {"disposition": "applied", "title": "iOS"}})
    write(work, CURSOR, {"channel": 10})
    (work / "source.py").write_text("original\n")
    commit(work)
    other = tmp_path / "other"
    git(tmp_path, "clone", str(remote), str(other))
    git(other, "config", "user.name", "Test")
    git(other, "config", "user.email", "test@example.invalid")
    return work, other, remote


def test_git_isolation_ignores_host_config_and_enclosing_push(tmp_path, monkeypatch):
    host_config = tmp_path / "host-gitconfig"
    host_config.write_text("[core]\n\thooksPath = /host-only-hooks\n")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(host_config))
    monkeypatch.setenv("GIT_DIR", str(tmp_path / "outside.git"))
    monkeypatch.setenv("GIT_INDEX_FILE", str(tmp_path / "outside-index"))
    isolate_git(tmp_path, monkeypatch)
    git(tmp_path, "init", "--bare", "--initial-branch=main")
    config = git(tmp_path, "config", "--list", "--show-origin")
    assert "host-gitconfig" not in config
    assert "core.hookspath" not in config.lower()
    assert git(tmp_path, "rev-parse", "--absolute-git-dir") == str(tmp_path.resolve())
    assert host_config.read_text() == "[core]\n\thooksPath = /host-only-hooks\n"


def test_remote_source_commit_preserved_and_checkout_untouched(repos, tmp_path):
    work, other, remote = repos
    snapshot = tmp_path / "base.json"
    head = git(work, "rev-parse", "HEAD")
    state.refresh(work, [SEEN], snapshot)
    write(work, SEEN, {"old": {"disposition": "applied", "title": "iOS"}, "ours": {"title": "AI"}})
    (work / "source.py").write_text("local unstaged work\n")
    staged = work / "staged.py"
    staged.write_text("local staged work\n")
    git(work, "add", "staged.py")
    index = git(work, "write-tree")
    (other / "source.py").write_text("new remote source\n")
    write(other, SEEN, {"old": {"disposition": "applied", "title": "iOS"}, "theirs": {"title": "Swift"}})
    commit(other)
    published = state.publish(work, snapshot, "chore(state): test")
    assert git(remote, "show", "main:source.py") == "new remote source"
    result = json.loads(git(remote, "show", f"main:{SEEN}"))
    assert set(result) == {"old", "ours", "theirs"}
    assert git(work, "rev-parse", "HEAD") == head
    assert git(work, "write-tree") == index
    assert (work / "source.py").read_text() == "local unstaged work\n"
    assert git(remote, "rev-parse", "main") == published
    assert not git(remote, "ls-tree", "main", "--", "staged.py")


def test_conflicting_decisions_fail_without_overwriting_remote(repos, tmp_path):
    work, other, remote = repos
    snapshot = tmp_path / "base.json"
    state.refresh(work, [SEEN], snapshot)
    write(work, SEEN, {"old": {"disposition": "dropped", "title": "iOS"}})
    write(other, SEEN, {"old": {"disposition": "archived", "title": "iOS"}})
    commit(other)
    remote_head = git(remote, "rev-parse", "main")
    with pytest.raises(state.StateConflict, match="Concurrent field conflict"):
        state.publish(work, snapshot, "chore(state): test")
    assert git(remote, "rev-parse", "main") == remote_head


def test_history_retained_and_cursor_never_rewinds(repos, tmp_path):
    work, other, remote = repos
    snapshot = tmp_path / "base.json"
    state.refresh(work, [SEEN, CURSOR], snapshot)
    write(work, SEEN, {})
    write(work, CURSOR, {"channel": 20})
    write(other, CURSOR, {"channel": 30})
    commit(other)
    state.publish(work, snapshot, "chore(state): test")
    assert json.loads(git(remote, "show", f"main:{SEEN}"))["old"]["disposition"] == "applied"
    assert json.loads(git(remote, "show", f"main:{CURSOR}")) == {"channel": 30}


def test_retry_remerges_when_push_loses_race(repos, tmp_path, monkeypatch):
    work, other, remote = repos
    snapshot = tmp_path / "base.json"
    state.refresh(work, [CURSOR], snapshot)
    write(work, CURSOR, {"channel": 20})
    actual_git = state.git
    pushes = []

    def raced_git(root, *args, **kwargs):
        if args[0] == "push":
            pushes.append(args)
            if len(pushes) == 1:
                write(other, CURSOR, {"channel": 30})
                commit(other)
        return actual_git(root, *args, **kwargs)

    monkeypatch.setattr(state, "git", raced_git)
    # The second merge becomes a no-op: the other writer advanced farther.
    assert state.publish(work, snapshot, "chore(state): test") is None
    assert len(pushes) == 1
    assert json.loads(git(remote, "show", f"main:{CURSOR}")) == {"channel": 30}


def test_push_permission_failure_is_not_retried(repos, tmp_path, monkeypatch):
    work, _, _ = repos
    snapshot = tmp_path / "base.json"
    state.refresh(work, [CURSOR], snapshot)
    write(work, CURSOR, {"channel": 20})
    actual_git = state.git
    pushes = []

    def rejected_git(root, *args, **kwargs):
        if args[0] == "push":
            pushes.append(args)
            raise subprocess.CalledProcessError(1, ["git", "push"])
        return actual_git(root, *args, **kwargs)

    monkeypatch.setattr(state, "git", rejected_git)
    with pytest.raises(subprocess.CalledProcessError):
        state.publish(work, snapshot, "chore(state): test")
    assert len(pushes) == 1


def test_claims_union_and_independent_history_fields():
    path = "database/collect_slots.json"
    assert state.merge_state({"days": {"d": {"slots": [9]}}}, {"days": {}},
                             {"days": {"d": {"slots": [12]}}}, path) == {"days": {"d": {"slots": [9, 12]}}}
    assert state.merge_state({"days": ["a"]}, {"days": ["b"]}, {"days": ["c"]},
                             "database/daily_email_days.json") == {"days": ["a", "b", "c"]}
    assert state.merge_state({"mail": {"kind": "ack"}}, {"mail": {"kind": "ack", "item_id": "id"}},
                             {"mail": {"kind": "reply"}}, "database/email_seen.json") == {
                                 "mail": {"kind": "reply", "item_id": "id"}}


def test_allowlist_and_malformed_state_fail_closed(repos, tmp_path):
    work, _, _ = repos
    with pytest.raises(ValueError, match="allowlisted"):
        state.refresh(work, ["source.py"], tmp_path / "base.json")
    snapshot = tmp_path / "base.json"
    state.refresh(work, [SEEN], snapshot)
    (work / SEEN).write_text("[]")
    with pytest.raises(state.StateConflict, match="JSON objects"):
        state.publish(work, snapshot, "chore(state): test")


def test_refresh_reads_latest_state_without_switching_code(repos, tmp_path):
    work, other, _ = repos
    (other / "source.py").write_text("new source\n")
    write(other, CURSOR, {"channel": 99})
    commit(other)
    state.refresh(work, [CURSOR], tmp_path / "base.json")
    assert json.loads((work / CURSOR).read_text()) == {"channel": 99}
    assert (work / "source.py").read_text() == "original\n"


def test_cli_writes_safe_failure_artifact(repos, tmp_path, monkeypatch, capsys):
    work, _, _ = repos
    snapshot = tmp_path / "base.json"
    state.refresh(work, [SEEN], snapshot)
    (work / SEEN).write_text("private invalid json")
    monkeypatch.chdir(work)
    monkeypatch.setattr("sys.argv", ["runtime_state.py", "publish", "--snapshot", str(snapshot)])
    assert state.main() == 1
    diagnostic = (work / "diagnostics/runtime-state-error.json").read_text()
    assert "JSONDecodeError" in diagnostic
    assert "private invalid json" not in diagnostic + capsys.readouterr().out


def test_invalid_claim_values_rejected():
    with pytest.raises(state.StateConflict, match="Invalid claim value"):
        state.merge_state({"days": []}, {"days": [{}]}, {"days": []}, "database/daily_email_days.json")
