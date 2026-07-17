# Self

## Architecture
A dependency-free Python newline-delimited JSON chatbot. `agent.py` validates and processes each non-empty input line independently while retaining an in-memory name map keyed by session for the process lifetime.

## Capabilities
- Compact, UTF-8 JSON output with one response per non-empty line
- Greetings, identity, deterministic fallback replies
- Per-session name learning and recall
- Malformed-request recovery without protocol contamination

## Known weaknesses
The chatbot intentionally uses a small deterministic rule set rather than open-ended language generation. State is ephemeral and ends with the process, as required by the protocol.

## Improvement strategy
Keep protocol behavior covered by subprocess tests, and add deterministic rules only when objective-grounded evidence requires them.
