"""Argument parsing and command handling for the todo application."""
from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from .store import StoreError, TodoStore


class FriendlyParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        self.print_usage(sys.stdout)
        print(f"Error: {message}")
        raise SystemExit(2)


def build_parser() -> argparse.ArgumentParser:
    parser = FriendlyParser(prog="todo", description="Manage a persistent local todo list.")
    parser.add_argument("--data-file", default=".todo.json", metavar="PATH",
                        help="JSON state file (default: .todo.json)")
    commands = parser.add_subparsers(dest="command", required=True, title="commands")
    add = commands.add_parser("add", help="add a pending todo")
    add.add_argument("title", help="todo title")
    commands.add_parser("list", help="list all todos")
    done = commands.add_parser("done", help="mark a todo completed")
    done.add_argument("id", type=positive_id, metavar="ID", help="positive todo ID")
    commands.add_parser("stats", help="show todo counts")
    return parser


def positive_id(value: str) -> int:
    try:
        ident = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("ID must be a positive integer") from exc
    if ident < 1:
        raise argparse.ArgumentTypeError("ID must be a positive integer")
    return ident


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "add" and not args.title.strip():
        print("Error: title must not be blank")
        return 2
    store = TodoStore(args.data_file)
    try:
        state = store.load()
        if args.command == "add":
            title = args.title.strip()
            ident = state["next_id"]
            state["todos"].append({"id": ident, "title": title, "completed": False})
            state["next_id"] = ident + 1
            store.save(state)
            print(f"Added #{ident}: {title}")
        elif args.command == "list":
            if not state["todos"]:
                print("No todos.")
            for item in sorted(state["todos"], key=lambda todo: todo["id"]):
                mark = "x" if item["completed"] else " "
                print(f"[{mark}] #{item['id']} {item['title']}")
        elif args.command == "done":
            item = next((todo for todo in state["todos"] if todo["id"] == args.id), None)
            if item is None:
                print(f"Error: todo #{args.id} not found")
                return 1
            if item["completed"]:
                print(f"Error: todo #{args.id} is already completed")
                return 1
            item["completed"] = True
            store.save(state)
            print(f"Completed #{item['id']}: {item['title']}")
        else:
            completed = sum(item["completed"] for item in state["todos"])
            print(f"Total: {len(state['todos'])}")
            print(f"Pending: {len(state['todos']) - completed}")
            print(f"Completed: {completed}")
        return 0
    except StoreError as exc:
        print(f"Error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
