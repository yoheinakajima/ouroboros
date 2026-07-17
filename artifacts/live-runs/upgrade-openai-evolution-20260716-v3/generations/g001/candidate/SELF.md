# Self

## Architecture
`todo.py` is a side-effect-free launcher into `todo_cli.cli`; parsing and command behavior live in `cli.py`, while validated UTF-8 JSON loading and atomic replacement writes live in `storage.py`.

## Capabilities
Supports argv `add`, `list [--all]`, `done`, and `stats`, isolated state via `--data-file`, stable IDs, parent creation, concise error status 2, and persistent state across processes.

## Validation
Six subprocess-driven unittest cases pass, including workflow persistence, help, malformed IDs/state, empty stores, and operation failures. Module imports and CLI help were also executed successfully.

## Known weaknesses
Concurrent writers are not serialized with a cross-process lock; each individual write is atomic, but simultaneous read-modify-write operations could lose an update.

## Improvement strategy
Retain the dependency-free design and add portable locking only if concurrent mutation becomes a stated requirement.
