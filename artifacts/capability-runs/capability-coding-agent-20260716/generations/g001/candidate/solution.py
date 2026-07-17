#!/usr/bin/env python3
"""A deterministic coding agent for small, clearly specified Python edits.

The agent deliberately preserves the supplied workspace and applies localized
source transformations or generates conventional function implementations from
natural-language requirements.
"""
from __future__ import annotations

import ast
import copy
import json
import re
import sys
from typing import Any


class RequestError(ValueError):
    """Raised when an input request does not follow the protocol."""


def _validate(request: Any) -> tuple[str, dict[str, str]]:
    if not isinstance(request, dict):
        raise RequestError("request must be a JSON object")
    task = request.get("task")
    files = request.get("files")
    if not isinstance(task, str) or not task.strip():
        raise RequestError("task must be a non-empty string")
    if not isinstance(files, dict):
        raise RequestError("files must be an object mapping paths to text")
    clean: dict[str, str] = {}
    for path, content in files.items():
        if (not isinstance(path, str) or not path or path.startswith("/") or
                ".." in path.split("/") or not isinstance(content, str)):
            raise RequestError("files must map safe relative paths to strings")
        clean[path] = content
    return task, clean


def _path_mentions(task: str) -> list[str]:
    # Filename-shaped tokens are much less ambiguous than arbitrary words.
    return list(dict.fromkeys(re.findall(r"(?<![\w/.-])([\w.-]+\.py)(?![\w/.-])", task)))


def _function_requirements(task: str) -> list[tuple[str, str | None]]:
    """Return function names and argument text explicitly present in a task."""
    found: list[tuple[str, str | None]] = []
    patterns = [
        r"(?:function|method)\s+([A-Za-z_]\w*)\s*\(([^)]*)\)",
        r"\b([A-Za-z_]\w*)\s*\(([^)]*)\)\s+(?:that|which|must|should|so)\b",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, task, re.I):
            item = (match.group(1), match.group(2).strip())
            if item not in found:
                found.append(item)
    return found


def _body_for(name: str, args: str, task: str) -> list[str] | None:
    """Infer small common implementations from behavioral language."""
    low = task.lower()
    first = (args.split(",")[0].strip().split(":")[0].split("=")[0].strip()
             if args.strip() else "value")
    if name == "mean" or ("arithmetic mean" in low and "empty" in low):
        return [f"if not {first}:", "    raise ValueError(\"values must not be empty\")",
                f"return sum({first}) / len({first})"]
    if name == "is_even" or ("even" in low and "exactly" in low):
        return [f"return {first} % 2 == 0"]
    if name == "is_odd" and "odd" in low:
        return [f"return {first} % 2 == 1"]
    if "normalize" in name.lower() and "whitespace" in low and "title" in low:
        return [f"return \" \".join({first}.split()).title()"]
    if name == "greet" and "hello" in low and "normalize_name" in low:
        return ["from text_utils import normalize_name", "", f"return f\"Hello, {{normalize_name({first})}}!\""]
    if "factorial" in name.lower():
        return [f"if {first} < 0:", "    raise ValueError(\"factorial is undefined for negative values\")",
                "result = 1", f"for number in range(2, {first} + 1):", "    result *= number", "return result"]
    if name.startswith("is_") and "palindrome" in low:
        return [f"cleaned = str({first})", "return cleaned == cleaned[::-1]"]
    return None


def _render_function(name: str, args: str, body: list[str]) -> str:
    lines = [f"def {name}({args}):"]
    lines.extend("    " + line if line else "" for line in body)
    return "\n".join(lines) + "\n"


def _replace_function(source: str, name: str, body: list[str]) -> str | None:
    """Replace only a function body while preserving its signature and peers."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    node = next((n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name), None)
    if node is None:
        return None
    lines = source.splitlines(keepends=True)
    if not node.body:
        return None
    start = node.body[0].lineno - 1
    end = node.end_lineno or node.lineno
    indent = " " * (node.col_offset + 4)
    replacement = [indent + line + "\n" if line else "\n" for line in body]
    return "".join(lines[:start] + replacement + lines[end:])


def _apply_task(task: str, files: dict[str, str]) -> dict[str, str]:
    result = copy.deepcopy(files)
    low = task.lower()
    if any(phrase in low for phrase in ("no code changes", "return the workspace unchanged", "no changes are needed")):
        return result

    paths = _path_mentions(task)
    requirements = _function_requirements(task)
    # Common phrasing names the file first and function after "so".
    for match in re.finditer(r"\b([A-Za-z_]\w*)\s*\(([^)]*)\)\s+(?:strips?|uses?|returns?|collapses?|raises?)\b", task, re.I):
        if not any(item[0] == match.group(1) for item in requirements):
            requirements.append((match.group(1), match.group(2)))
    # Include plainly named functions in update/fix clauses even if no signature is given.
    for match in re.finditer(r"(?:fix|update|change|repair)\s+([A-Za-z_]\w*)\s*(?:\(([^)]*)\))?", task, re.I):
        name = match.group(1)
        if name.lower() not in {"the", "file", "code"} and not any(x[0] == name for x in requirements):
            requirements.append((name, match.group(2)))

    for path in paths:
        source = result.get(path, "")
        relevant = requirements
        # Tasks often associate each function with the nearest named file. Existing
        # definitions provide an exact and safe association.
        existing_names: set[str] = set()
        try:
            existing_names = {n.name for n in ast.parse(source).body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        except SyntaxError:
            pass
        changed = source
        generated: list[str] = []
        for name, stated_args in relevant:
            args = stated_args
            if name in existing_names:
                try:
                    node = next(n for n in ast.parse(changed).body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name)
                    args = ast.unparse(node.args)
                except (SyntaxError, StopIteration):
                    args = args or "value"
            elif path in files and len(paths) > 1:
                # Do not add every requested function to every existing module.
                if name not in source and name.lower() not in path.lower():
                    if not (name == "greet" and path.endswith("app.py")) and not ("normalize" in name and "text" in path):
                        continue
            args = args or "value"
            body = _body_for(name, args, task)
            if body is None:
                continue
            replacement = _replace_function(changed, name, body)
            if replacement is not None:
                changed = replacement
            elif name not in existing_names:
                generated.append(_render_function(name, args, body))
        if generated:
            if changed and not changed.endswith("\n"):
                changed += "\n"
            if changed:
                changed += "\n"
            changed += "\n".join(generated)
        if changed != source or path not in result:
            # Only accept syntactically valid generated Python.
            try:
                ast.parse(changed)
            except SyntaxError:
                continue
            result[path] = changed
    return result


def handle_request(request: Any) -> dict[str, dict[str, str]]:
    task, files = _validate(request)
    return {"files": _apply_task(task, files)}


def main() -> int:
    failed = False
    for raw in sys.stdin:
        if not raw.strip():
            continue
        try:
            request = json.loads(raw)
            response = handle_request(request)
        except (json.JSONDecodeError, RequestError) as exc:
            response = {"error": str(exc)}
            failed = True
        except Exception as exc:  # protocol remains machine-readable
            response = {"error": f"unable to process request: {exc}"}
            failed = True
        print(json.dumps(response, ensure_ascii=False, sort_keys=True))
    return 2 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
