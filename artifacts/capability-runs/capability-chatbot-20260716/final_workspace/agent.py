#!/usr/bin/env python3
"""A deterministic newline-delimited JSON chatbot."""
import json
import re
import sys

NAME_PATTERN = re.compile(r"^My name is\s+(.+?)\.$", re.IGNORECASE)


def reply_to(message, session, names):
    """Return the response text and update per-session state when appropriate."""
    normalized = message.strip().casefold()
    if normalized in {"hello", "hi", "hey"}:
        return "Hello! How can I help you?"
    if normalized == "who are you?":
        return "I am a chatbot."

    match = NAME_PATTERN.fullmatch(message.strip())
    if match:
        name = match.group(1).strip()
        if name:
            names[session] = name
            return f"Nice to meet you, {name}!"

    if normalized == "what is my name?":
        name = names.get(session)
        return f"Your name is {name}." if name else "I don't know your name yet."

    return f"You said: {message}"


def main():
    names = {}
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            request = json.loads(line)
            if not isinstance(request, dict):
                raise ValueError
            message = request.get("message")
            session = request.get("session", "default")
            if not isinstance(message, str) or not isinstance(session, str):
                raise ValueError
            response = {"session": session, "reply": reply_to(message, session, names)}
        except (json.JSONDecodeError, ValueError):
            response = {"error": "Invalid request"}
        print(json.dumps(response, ensure_ascii=False, separators=(",", ":")), flush=True)


if __name__ == "__main__":
    main()
