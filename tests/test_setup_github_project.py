from __future__ import annotations

import os
import subprocess

from scripts import setup_github_project


def test_graphql_uses_private_temp_file(monkeypatch):
    seen = {}

    def fake_run(command, **kwargs):
        seen["command"] = command
        seen["path"] = command[-1]
        seen["mode"] = oct(os.stat(command[-1]).st_mode & 0o777)
        return subprocess.CompletedProcess(command, 0, stdout='{"data":{"ok":true}}', stderr="")

    monkeypatch.setattr(setup_github_project.subprocess, "run", fake_run)
    assert setup_github_project.graphql("query { ok }") == {"ok": True}
    assert seen["mode"] == "0o600"
    assert not os.path.exists(seen["path"])
