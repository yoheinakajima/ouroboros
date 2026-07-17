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

Terminal-Bench is the persistence exception within this boundary: Harbor starts
one fresh official task environment per attempt, and the brokered agent's shell
commands persist inside that environment until Harbor runs its separate
verifier. Provider inference still runs on the host, credentials are never
forwarded, and the entire task environment is removed after the attempt.

## Local reference setup

```bash
brew install colima docker docker-buildx docker-compose qemu lima-additional-guestagents
mkdir -p ~/.docker/cli-plugins
ln -sfn "$(brew --prefix docker-buildx)/bin/docker-buildx" ~/.docker/cli-plugins/docker-buildx
ln -sfn "$(brew --prefix docker-compose)/bin/docker-compose" ~/.docker/cli-plugins/docker-compose
colima start --profile ouro-x86 --runtime docker --arch x86_64 --vm-type qemu \
  --cpu 8 --memory 16 --disk 200
docker buildx version
python -m research.sandbox --check
```

The full x86 guest is the no-license reference path for linux/amd64 Terminal
tasks on Apple silicon. It is slower than a native host but avoids compiler
crashes seen with per-process emulation. Operators running native x86 Linux can
use Docker directly. Docker Buildx is required because Harbor constructs a
dedicated egress-control sidecar for `no-network` verifier execution. The
readiness gate checks that the plugin is callable before a scored run begins.
