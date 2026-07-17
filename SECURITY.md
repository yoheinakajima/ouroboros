# Security policy

Ouroboros executes model-selected commands and can evaluate generated Python.
Treat it as experimental software and run untrusted objectives only in a
disposable container or VM. The subprocess and AST checks reduce accidents;
they are not a hostile-code security boundary.

Never expose provider keys to evolved workspaces, candidate Packs, test
commands, or grader containers. Use the host-owned broker and scoped
capabilities. Do not run the research harness on repositories or data you are
not prepared to modify or disclose in traces.

Please report suspected credential exposure, path escape, sandbox escape,
hash-verification bypass, hidden-evaluator leakage, or unsafe promotion
privately to the repository owner. Do not include real secrets or exploit an
issue against third-party systems.
