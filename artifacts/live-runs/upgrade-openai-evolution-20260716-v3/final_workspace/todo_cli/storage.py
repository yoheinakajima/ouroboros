"""Validated JSON persistence for the todo application."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


class StorageError(Exception):
    """A user-facing persistence or state validation error."""


class TodoStore:
    """Load and atomically save todos in a selected local JSON file."""

    def __init__(self, path: str | os.PathLike[str]):
        self.path = Path(path).expanduser()

    def load(self) -> dict[str, Any]:
        try:
            with self.path.open("r", encoding="utf-8") as stream:
                raw = json.load(stream)
        except FileNotFoundError:
            return {"next_id": 1, "todos": []}
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise StorageError(f"state file is not valid JSON: {self.path}") from exc
        except OSError as exc:
            raise StorageError(f"cannot read state file '{self.path}': {exc.strerror or exc}") from exc
        return self._validate(raw)

    @staticmethod
    def _validate(raw: Any) -> dict[str, Any]:
        if not isinstance(raw, dict):
            raise StorageError("state file must contain a JSON object")
        todos = raw.get("todos")
        next_id = raw.get("next_id")
        if not isinstance(todos, list) or isinstance(next_id, bool) or not isinstance(next_id, int) or next_id < 1:
            raise StorageError("state file has an invalid schema")
        seen: set[int] = set()
        clean = []
        for item in todos:
            if not isinstance(item, dict):
                raise StorageError("state file contains an invalid todo")
            ident, title, completed = item.get("id"), item.get("title"), item.get("completed")
            if (isinstance(ident, bool) or not isinstance(ident, int) or ident < 1 or ident in seen
                    or not isinstance(title, str) or not title.strip() or not isinstance(completed, bool)):
                raise StorageError("state file contains an invalid todo")
            seen.add(ident)
            clean.append({"id": ident, "title": title, "completed": completed})
        if seen and next_id <= max(seen):
            raise StorageError("state file has an invalid next_id")
        return {"next_id": next_id, "todos": clean}

    def save(self, state: dict[str, Any]) -> None:
        state = self._validate(state)
        parent = self.path.parent
        temporary: str | None = None
        try:
            parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=parent,
                prefix=f".{self.path.name}.", suffix=".tmp", delete=False
            ) as stream:
                temporary = stream.name
                json.dump(state, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        except OSError as exc:
            if temporary:
                try:
                    os.unlink(temporary)
                except OSError:
                    pass
            raise StorageError(f"cannot write state file '{self.path}': {exc.strerror or exc}") from exc
