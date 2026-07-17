"""Validated, atomic JSON persistence for todos."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


class StoreError(Exception):
    """State could not safely be read or written."""


class TodoStore:
    def __init__(self, path: str | os.PathLike[str]):
        self.path = Path(path)

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"version": 1, "next_id": 1, "todos": []}
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                state = json.load(handle)
        except (OSError, UnicodeError) as exc:
            raise StoreError(f"cannot read state file '{self.path}': {exc}") from exc
        except json.JSONDecodeError as exc:
            raise StoreError(
                f"malformed JSON in state file '{self.path}' at line {exc.lineno}, column {exc.colno}"
            ) from exc
        self._validate(state)
        return state

    @staticmethod
    def _validate(state: Any) -> None:
        if not isinstance(state, dict):
            raise StoreError("incompatible state: JSON root must be an object")
        if state.get("version") != 1:
            raise StoreError("incompatible state: unsupported or missing version")
        next_id = state.get("next_id")
        todos = state.get("todos")
        if type(next_id) is not int or next_id < 1 or not isinstance(todos, list):
            raise StoreError("incompatible state: invalid next_id or todos")
        ids: set[int] = set()
        for item in todos:
            if not isinstance(item, dict) or set(item) != {"id", "title", "completed"}:
                raise StoreError("incompatible state: invalid todo record")
            ident = item["id"]
            if (type(ident) is not int or ident < 1 or ident in ids
                    or not isinstance(item["title"], str) or not item["title"].strip()
                    or type(item["completed"]) is not bool):
                raise StoreError("incompatible state: invalid todo record")
            ids.add(ident)
        if ids and next_id <= max(ids):
            raise StoreError("incompatible state: next_id does not exceed existing IDs")

    def save(self, state: dict[str, Any]) -> None:
        self._validate(state)
        parent = self.path.parent
        try:
            parent.mkdir(parents=True, exist_ok=True)
            fd, temporary = tempfile.mkstemp(prefix=f".{self.path.name}.", suffix=".tmp", dir=parent)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(state, handle, indent=2, ensure_ascii=False)
                    handle.write("\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary, self.path)
            except BaseException:
                try:
                    os.unlink(temporary)
                except OSError:
                    pass
                raise
        except OSError as exc:
            raise StoreError(f"cannot write state file '{self.path}': {exc}") from exc
