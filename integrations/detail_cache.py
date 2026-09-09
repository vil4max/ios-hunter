from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
import threading
import time
from pathlib import Path

_CACHE_LOCK = threading.RLock()
TTL_SECONDS = 6 * 60 * 60
MAX_ENTRIES = 256
MAX_DESCRIPTION_LENGTH = 200_000


class DetailCache:
    """Optional cache of verified public descriptions; never serves expired data."""

    def __init__(self, path: Path | None, *, ttl: float = TTL_SECONDS):
        self.path = path
        self.ttl = ttl

    @classmethod
    def from_environment(cls):
        value = os.getenv("DETAIL_CACHE_PATH", "").strip()
        return cls(Path(value) if value else None)

    def _key(self, url: str, title: str) -> str:
        return hashlib.sha256(json.dumps([url, title]).encode()).hexdigest()

    def _read(self) -> dict:
        if self.path is None:
            return {}
        try:
            if self.path.stat().st_size > MAX_ENTRIES * (MAX_DESCRIPTION_LENGTH + 2000):
                return {}
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict) or payload.get("version") != 1:
                return {}
            entries = payload.get("entries")
            if not isinstance(entries, dict):
                return {}
            now = time.time()
            valid = {}
            for key, entry in entries.items():
                if not isinstance(entry, dict):
                    continue
                saved = entry.get("saved_at")
                description = entry.get("description")
                location = entry.get("location")
                if (not isinstance(saved, (int, float)) or not math.isfinite(saved)
                        or not 0 <= now - saved < self.ttl
                        or not isinstance(description, str) or not description
                        or len(description) > MAX_DESCRIPTION_LENGTH
                        or (location is not None and not isinstance(location, str))):
                    continue
                valid[key] = entry
            return dict(sorted(valid.items(), key=lambda item: item[1]["saved_at"])[-MAX_ENTRIES:])
        except (OSError, ValueError, TypeError):
            return {}

    def get(self, url: str, title: str) -> tuple[str, str | None] | None:
        with _CACHE_LOCK:
            entry = self._read().get(self._key(url, title))
        return (entry["description"], entry.get("location")) if entry else None

    def put(self, url: str, title: str, description: str, location: str | None) -> None:
        if self.path is None or not description or len(description) > MAX_DESCRIPTION_LENGTH:
            return
        with _CACHE_LOCK:
            entries = self._read()
            entries[self._key(url, title)] = {
                "saved_at": time.time(), "description": description, "location": location,
            }
            entries = dict(sorted(entries.items(), key=lambda item: item[1]["saved_at"])[-MAX_ENTRIES:])
            temporary = None
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.path.parent,
                                                 prefix=".detail-cache-", delete=False) as stream:
                    temporary = stream.name
                    json.dump({"version": 1, "entries": entries}, stream, ensure_ascii=False)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, self.path)
            except OSError:
                # A cache is optional acceleration; storage failures cannot drop live jobs.
                pass
            finally:
                if temporary:
                    try:
                        os.unlink(temporary)
                    except OSError:
                        pass
