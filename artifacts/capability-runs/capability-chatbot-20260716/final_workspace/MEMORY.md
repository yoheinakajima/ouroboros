# Memory

- The entrypoint protocol is newline-delimited JSON, so input must be processed line by line rather than parsed as one JSON document.
- Keep conversation state in memory and key it by session to prevent cross-session leakage.
- Use compact JSON separators and reserve stdout exclusively for protocol responses.
- Catch malformed JSON and schema errors per line so later requests continue processing.
- Subprocess tests verify exit status, stderr cleanliness, stateful behavior, and invalid-input recovery.
