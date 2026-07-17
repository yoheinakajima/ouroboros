# Self

## Architecture
A thin `todo.py` argv entrypoint delegates parsing and command handling to `todo_cli.cli`; `todo_cli.store` owns strict JSON validation and atomic persistence.

## Capabilities
Adds, lists, completes, and summarizes todos across processes using a configurable JSON file. Reports usage and operational failures without tracebacks.

## Validation
Subprocess integration tests exercise lifecycle persistence, statistics, malformed state, missing and completed IDs, blank titles, and invalid arguments.

## Known weaknesses
Concurrent writers are not serialized with an inter-process lock.

## Improvement strategy
Preserve portable standard-library behavior and extend tests before changing persisted schema.
