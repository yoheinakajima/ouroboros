# Memory

- For argv applications, keep the entrypoint thin and test separate processes against temporary state paths.
- Validate the complete persisted schema before commands mutate it; malformed state must remain untouched.
- Write JSON through a same-directory temporary file, fsync it, and atomically replace the destination.
- Route argparse diagnostics to stdout when the executable contract inspects stdout for `Error:`.
