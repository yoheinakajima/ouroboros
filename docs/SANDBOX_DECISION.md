# Sandbox decision

Ouroboros uses a local OCI container runtime as the default isolation boundary
for benchmark attempts. On Apple silicon macOS, the reference no-account setup
is Docker Engine inside [Colima](https://github.com/abiosoft/colima). Colima is
MIT-licensed, runs locally, and does not require a hosted-service account.

## Why E2B is optional, not the default

E2B is useful infrastructure and remains a plausible future backend. Its hosted
SDK requires an `E2B_API_KEY`, however. The open-source E2B components are
Apache-2.0 licensed and self-hostable, but the official deployment is a full
Firecracker-oriented cloud stack with Terraform, Packer, PostgreSQL, networking,
and cloud compute prerequisites. It is not a lightweight local macOS sandbox.

The benchmark therefore treats E2B as an optional remote backend, not a required
dependency and not a way to avoid credentials. An E2B adapter must remain
disabled unless the operator explicitly configures either hosted E2B credentials
or a separately managed self-hosted control plane.

## Required isolation properties

The scored backend launches every attempt in a fresh container with:

- a digest-pinned image;
- no network by default;
- no provider credentials in the container environment;
- a non-root user, all Linux capabilities dropped, and no-new-privileges;
- a read-only root filesystem plus bounded temporary storage;
- explicit CPU, memory, process, output, and wall-clock limits;
- only the attempt workspace mounted read-write;
- no grader, hidden-test, broker-journal, or host-control-plane mount; and
- forced cleanup after success, failure, or timeout.

The model provider, budget ledger, and audit journal remain in a trusted host
broker outside the candidate container. Grading runs later in a separate fresh
container. A container is a practical benchmark containment boundary, not a
claim of perfect isolation against a kernel exploit; adversarial public service
operation still warrants disposable hosts or hardened microVM infrastructure.

## Local reference setup

```bash
brew install colima docker
colima start --runtime docker --vm-type vz --cpu 4 --memory 8 --disk 60
python -m research.sandbox --check
```

Buildx is not required for benchmark execution. Homebrew installs it separately
if multi-platform image building is later needed.
