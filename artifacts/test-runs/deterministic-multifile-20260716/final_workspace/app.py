#!/usr/bin/env python3
import json
import sys
from logic import transform

payload = json.loads(sys.stdin.read() or "{}")
print(json.dumps({"result": transform(str(payload.get("input", ""))) }))
