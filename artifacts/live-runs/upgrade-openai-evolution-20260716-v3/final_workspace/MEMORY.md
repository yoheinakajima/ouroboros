# Memory

- For local JSON state, validate all loaded fields before command logic and convert JSON, Unicode, and filesystem failures into user-facing errors without tracebacks.
- Write mutations through a temporary file in the destination directory, flush/fsync, then `os.replace` to prevent partial state files.
- Exercise persistence using independent subprocess calls and temporary state paths; this validates the real argv launcher and process boundaries.
