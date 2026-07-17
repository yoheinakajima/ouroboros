"""Argument parsing and commands for the todo CLI."""
from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence

from .storage import StorageError, TodoStore

DEFAULT_DATA_FILE = os.environ.get("TODO_DATA_FILE", ".todo.json")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Manage a persistent local todo list.")
    result.add_argument("--data-file", default=DEFAULT_DATA_FILE, metavar="PATH", help="JSON state file (default: .todo.json)")
    commands = result.add_subparsers(dest="command", required=True)
    add = commands.add_parser("add", help="add a pending todo")
    add.add_argument("title", help="todo title")
    listing = commands.add_parser("list", help="list pending todos")
    listing.add_argument("--all", action="store_true", help="include completed todos")
    done = commands.add_parser("done", help="complete a todo")
    done.add_argument("id", type=positive_id, metavar="ID", help="positive todo ID")
    commands.add_parser("stats", help="show todo counts")
    return result


def positive_id(value: str) -> int:
    try:
        ident = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("ID must be a positive integer") from exc
    if ident < 1:
        raise argparse.ArgumentTypeError("ID must be a positive integer")
    return ident


def execute(args: argparse.Namespace, store: TodoStore) -> None:
    state = store.load()
    todos = state["todos"]
    if args.command == "add":
        title = args.title.strip()
        if not title:
            raise ValueError("todo title cannot be blank")
        item = {"id": state["next_id"], "title": title, "completed": False}
        todos.append(item)
        state["next_id"] += 1
        store.save(state)
        print(f"Added todo {item['id']}: {title}")
    elif args.command == "list":
        visible = sorted((item for item in todos if args.all or not item["completed"]), key=lambda item: item["id"])
        if not visible:
            print("No todos." if args.all else "No pending todos.")
        for item in visible:
            mark = "x" if item["completed"] else " "
            print(f"[{mark}] {item['id']}: {item['title']}")
    elif args.command == "done":
        item = next((item for item in todos if item["id"] == args.id), None)
        if item is None:
            raise ValueError(f"todo {args.id} does not exist")
        if item["completed"]:
            raise ValueError(f"todo {args.id} is already completed")
        item["completed"] = True
        store.save(state)
        print(f"Completed todo {item['id']}: {item['title']}")
    else:
        completed = sum(item["completed"] for item in todos)
        print(f"Total: {len(todos)}")
        print(f"Pending: {len(todos) - completed}")
        print(f"Completed: {completed}")


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        execute(args, TodoStore(args.data_file))
    except (StorageError, ValueError) as exc:
        print(f"todo: error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
