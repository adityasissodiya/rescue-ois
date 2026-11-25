"""Durable state for signing agents and verifiers (spec/protocol.md, s. 6.4 and 8).

``MemoryStore`` models durable storage inside the simulator: ``commit`` is the durable
write, and a crash keeps only what was committed. ``FileStore`` performs a real durable
write (temporary file, fsync, atomic rename, fsync of the directory).
"""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path


class MemoryStore:
    def __init__(self, initial: dict):
        self._durable = copy.deepcopy(initial)
        self.commits = 0

    def load(self) -> dict:
        return copy.deepcopy(self._durable)

    def commit(self, state: dict) -> None:
        self._durable = copy.deepcopy(state)
        self.commits += 1


class FileStore:
    def __init__(self, path: str | os.PathLike, initial: dict | None = None):
        self.path = Path(path)
        self.commits = 0
        if not self.path.exists():
            if initial is None:
                raise FileNotFoundError(self.path)
            self.commit(initial)

    def load(self) -> dict:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def commit(self, state: dict) -> None:
        tmp = self.path.with_name(self.path.name + ".tmp")
        data = json.dumps(state, sort_keys=True).encode("utf-8")
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            os.write(fd, data)
            os.fsync(fd)
        finally:
            os.close(fd)
        os.replace(tmp, self.path)
        dfd = os.open(self.path.parent, os.O_RDONLY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
        self.commits += 1
