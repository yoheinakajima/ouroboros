# Self

## Architecture
Importable standard-library Python coding agent with a validated JSONL CLI. It preserves the complete supplied workspace and uses AST-bounded function-body edits plus conservative generation for explicit small tasks.

## Capabilities
Creates mean-style utility modules, repairs parity predicates, coordinates name normalization and greeting changes, validates paths and request types, and returns machine-readable errors.

## Known weaknesses
Natural-language synthesis is intentionally bounded to recognizable behavioral patterns; ambiguous or broad engineering requests are preserved rather than guessed.

## Improvement strategy
Add only behavior patterns supported by executable tests while retaining localized AST edits and complete-workspace preservation.
