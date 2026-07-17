# Security policy

Ouroboros executes model-selected commands and can evaluate generated Python.
Treat it as experimental software. Common benchmark commands run in disposable,
digest-pinned OCI containers; graders use distinct read-only private and
submission mounts plus a separate writable score mount. Containers are still
not a kernel-level proof against hostile code, so public adversarial operation
warrants disposable hosts or hardened microVM infrastructure. Native mutation
subprocesses and AST checks reduce accidents but are not a hostile-code boundary.

The agent/model never receives grader mounts. Code executed later by a suite's
grader must still be treated as hostile: a read-only mount prevents mutation,
not observation by that executing code. High-assurance hidden-test service
requires a suite-specific two-stage evaluator or a stronger VM boundary.

Never expose provider keys to evolved workspaces, candidate Packs, test
commands, or grader containers. Use the host-owned broker and scoped
capabilities. Do not run the research harness on repositories or data you are
not prepared to modify or disclose in traces.

Please report suspected credential exposure, path escape, sandbox escape,
hash-verification bypass, hidden-evaluator leakage, or unsafe promotion
privately to the repository owner. Do not include real secrets or exploit an
issue against third-party systems.
