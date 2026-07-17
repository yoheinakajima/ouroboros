# Contributing

Ouroboros welcomes small, auditable improvements to the agent, research
protocol, adapters, tasks, and evaluators.

Use Python 3.11 or newer and install the development environment with:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m unittest discover -s tests -p 'test_*.py'
ruff check ouroboros.py research tests
python -m research.readiness --development
```

Do not commit `.env` files, raw provider responses containing secrets, hidden
evaluation cases, or generated run directories. A benchmark change must state
whether it affects the prompt, grader, task selection, source hash, budget, or
retry policy. Such changes require a new protocol version; existing results
must never be silently reinterpreted under the new version.

Pull requests should include deterministic tests and describe the authority
added by any new tool, import, capability, or generated-code surface.
