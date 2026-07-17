#!/usr/bin/env python3
import json
import sys

def main():
    payload = json.loads(sys.stdin.read() or "{}")
    value = str(payload.get("input", payload.get("objective", "")))
    print(json.dumps({"result": value, "status": "seed"}))

if __name__ == "__main__":
    main()
