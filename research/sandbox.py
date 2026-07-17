#!/usr/bin/env python3
"""Fresh, key-free OCI containers for candidate-controlled commands."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Mapping, Sequence

_DIGEST_IMAGE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._/:@-]*@sha256:[0-9a-f]{64}$")
_LOCAL_IMAGE_ID = re.compile(r"^sha256:[0-9a-f]{64}$")
_ENV_NAME = re.compile(r"^[A-Z_][A-Z0-9_]*$")
_PROVIDER_MARKERS = ("API_KEY", "ACCESS_KEY", "SECRET", "TOKEN", "PASSWORD", "CREDENTIAL")


class SandboxError(RuntimeError):
    """The isolation boundary could not execute a requested command safely."""


@dataclass(frozen=True)
class SandboxLimits:
    wall_seconds: float = 120.0
    memory_mb: int = 2048
    cpus: float = 2.0
    pids: int = 256
    tmpfs_mb: int = 256
    output_bytes: int = 1_000_000

    def validate(self) -> None:
        if self.wall_seconds <= 0:
            raise ValueError("wall_seconds must be positive")
        if self.memory_mb < 64 or self.cpus <= 0 or self.pids < 16 or self.tmpfs_mb < 16:
            raise ValueError("sandbox resource limits are implausibly small")
        if self.output_bytes < 1024:
            raise ValueError("output_bytes must be at least 1024")


@dataclass(frozen=True)
class SandboxResult:
    command: tuple[str, ...]
    image: str
    returncode: int
    stdout: str
    stderr: str
    duration_seconds: float
    timed_out: bool
    output_truncated: bool
    container_name: str
    security_profile: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _safe_environment(values: Mapping[str, str] | None) -> dict[str, str]:
    safe: dict[str, str] = {}
    for name, value in (values or {}).items():
        if not _ENV_NAME.fullmatch(name):
            raise ValueError(f"invalid environment variable name: {name!r}")
        if any(marker in name for marker in _PROVIDER_MARKERS):
            raise ValueError(f"credential-like environment variable denied: {name}")
        if "\x00" in value:
            raise ValueError(f"NUL byte in environment variable: {name}")
        safe[name] = value
    return safe


def docker_status(*, docker_binary: str = "docker", timeout: float = 10.0) -> dict[str, object]:
    """Return a stable no-mutation health report for the Docker daemon."""

    try:
        result = subprocess.run(
            [docker_binary, "info", "--format", "{{json .}}"],
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ready": False, "error": f"{type(exc).__name__}: {exc}"}
    if result.returncode != 0:
        return {"ready": False, "error": result.stderr.strip() or result.stdout.strip()}
    try:
        info = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return {"ready": False, "error": f"invalid docker info: {exc}"}
    return {
        "ready": True,
        "server_version": info.get("ServerVersion"),
        "architecture": info.get("Architecture"),
        "operating_system": info.get("OperatingSystem"),
        "security_options": info.get("SecurityOptions", []),
    }


class DockerSandbox:
    """Run one argv command in one fresh, least-authority container."""

    def __init__(self, *, docker_binary: str = "docker") -> None:
        self.docker_binary = docker_binary

    @staticmethod
    def validate_image(image: str) -> None:
        if not (_DIGEST_IMAGE.fullmatch(image) or _LOCAL_IMAGE_ID.fullmatch(image)):
            raise ValueError(
                "container image must be a repo@sha256:<64 hex> reference or a local sha256:<64 hex> image ID"
            )

    def _docker_command(
        self,
        *,
        image: str,
        workspace: Path,
        command: Sequence[str],
        limits: SandboxLimits,
        environment: Mapping[str, str],
        container_name: str,
        network: bool,
    ) -> list[str]:
        network_mode = "bridge" if network else "none"
        invocation = [
            self.docker_binary,
            "run",
            "--rm",
            "--pull=never",
            "--name",
            container_name,
            "--label",
            "dev.ouroboros.boundary=attempt",
            "--network",
            network_mode,
            "--read-only",
            "--cap-drop=ALL",
            "--security-opt",
            "no-new-privileges:true",
            "--pids-limit",
            str(limits.pids),
            "--memory",
            f"{limits.memory_mb}m",
            "--cpus",
            str(limits.cpus),
            "--tmpfs",
            f"/tmp:rw,noexec,nosuid,nodev,size={limits.tmpfs_mb}m,mode=1777",
            "--user",
            "65532:65532",
            "--workdir",
            "/workspace",
            "--mount",
            f"type=bind,src={workspace},dst=/workspace",
            "--env",
            "HOME=/tmp/home",
            "--env",
            "OUROBOROS_SANDBOX=1",
        ]
        for name in sorted(environment):
            invocation.extend(["--env", f"{name}={environment[name]}"])
        invocation.append(image)
        invocation.extend(command)
        return invocation

    def run(
        self,
        *,
        image: str,
        workspace: str | Path,
        command: Sequence[str],
        limits: SandboxLimits | None = None,
        environment: Mapping[str, str] | None = None,
        network: bool = False,
    ) -> SandboxResult:
        self.validate_image(image)
        selected_limits = limits or SandboxLimits()
        selected_limits.validate()
        root = Path(workspace).resolve(strict=True)
        if not root.is_dir() or root.is_symlink():
            raise ValueError("workspace must be a real directory, not a symlink")
        argv = tuple(str(item) for item in command)
        if not argv or any(not item or "\x00" in item for item in argv):
            raise ValueError("command must be a nonempty argv without NUL bytes")
        safe_env = _safe_environment(environment)
        container_name = f"ouroboros-{uuid.uuid4().hex}"
        docker_argv = self._docker_command(
            image=image,
            workspace=root,
            command=argv,
            limits=selected_limits,
            environment=safe_env,
            container_name=container_name,
            network=network,
        )
        return self._execute(
            docker_argv,
            argv=argv,
            image=image,
            container_name=container_name,
            limits=selected_limits,
            security_profile={
                "network": "bridge" if network else "none",
                "read_only_root": True,
                "capabilities": [],
                "no_new_privileges": True,
                "user": "65532:65532",
                "workspace_mount": "/workspace:rw",
                "provider_credentials_forwarded": False,
                "limits": asdict(selected_limits),
            },
        )

    def run_grader(
        self,
        *,
        image: str,
        grader_workspace: str | Path,
        submission: str | Path,
        output_workspace: str | Path,
        command: Sequence[str],
        limits: SandboxLimits | None = None,
        environment: Mapping[str, str] | None = None,
    ) -> SandboxResult:
        """Run a grader with private code, submission, and output on separate mounts."""

        self.validate_image(image)
        selected_limits = limits or SandboxLimits()
        selected_limits.validate()
        grader = Path(grader_workspace).resolve(strict=True)
        candidate = Path(submission).resolve(strict=True)
        output = Path(output_workspace).resolve(strict=True)
        for label, path in (("grader", grader), ("submission", candidate), ("output", output)):
            if not path.is_dir() or path.is_symlink():
                raise ValueError(f"{label} workspace must be a real directory")
        if len({grader, candidate, output}) != 3:
            raise ValueError("grader, submission, and output workspaces must be distinct")
        for left, right in ((grader, candidate), (grader, output), (candidate, output)):
            if left in right.parents or right in left.parents:
                raise ValueError("sealed grader workspaces may not contain one another")
        output.chmod(output.stat().st_mode | 0o777)
        argv = tuple(str(item) for item in command)
        if not argv or any(not item or "\x00" in item for item in argv):
            raise ValueError("command must be a nonempty argv without NUL bytes")
        safe_env = _safe_environment(environment)
        container_name = f"ouroboros-grader-{uuid.uuid4().hex}"
        invocation = [
            self.docker_binary,
            "run",
            "--rm",
            "--pull=never",
            "--name",
            container_name,
            "--label",
            "dev.ouroboros.boundary=grader",
            "--network",
            "none",
            "--read-only",
            "--cap-drop=ALL",
            "--security-opt",
            "no-new-privileges:true",
            "--pids-limit",
            str(selected_limits.pids),
            "--memory",
            f"{selected_limits.memory_mb}m",
            "--cpus",
            str(selected_limits.cpus),
            "--tmpfs",
            f"/tmp:rw,noexec,nosuid,nodev,size={selected_limits.tmpfs_mb}m,mode=1777",
            "--user",
            "65532:65532",
            "--workdir",
            "/grader",
            "--mount",
            f"type=bind,src={grader},dst=/grader,readonly",
            "--mount",
            f"type=bind,src={candidate},dst=/submission,readonly",
            "--mount",
            f"type=bind,src={output},dst=/output",
            "--env",
            "HOME=/tmp/home",
            "--env",
            "OUROBOROS_SANDBOX=1",
            "--env",
            "OUROBOROS_SUBMISSION=/submission",
            "--env",
            "OUROBOROS_SCORE_PATH=/output/score.json",
        ]
        for name in sorted(safe_env):
            invocation.extend(["--env", f"{name}={safe_env[name]}"])
        invocation.append(image)
        invocation.extend(argv)
        return self._execute(
            invocation,
            argv=argv,
            image=image,
            container_name=container_name,
            limits=selected_limits,
            security_profile={
                "network": "none",
                "read_only_root": True,
                "capabilities": [],
                "no_new_privileges": True,
                "user": "65532:65532",
                "grader_mount": "/grader:ro",
                "submission_mount": "/submission:ro",
                "output_mount": "/output:rw",
                "provider_credentials_forwarded": False,
                "limits": asdict(selected_limits),
            },
        )

    def _execute(
        self,
        docker_argv: Sequence[str],
        *,
        argv: tuple[str, ...],
        image: str,
        container_name: str,
        limits: SandboxLimits,
        security_profile: dict[str, object],
    ) -> SandboxResult:
        started = time.monotonic()
        timed_out = False
        try:
            process = subprocess.Popen(
                docker_argv,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=os.environ.copy(),
            )
        except OSError as exc:
            raise SandboxError(f"could not start docker: {exc}") from exc
        stdout_buffer = bytearray()
        stderr_buffer = bytearray()
        stdout_state = {"truncated": False}
        stderr_state = {"truncated": False}
        stdout_thread = threading.Thread(
            target=self._drain_bounded,
            args=(process.stdout, stdout_buffer, limits.output_bytes, stdout_state),
            daemon=True,
        )
        stderr_thread = threading.Thread(
            target=self._drain_bounded,
            args=(process.stderr, stderr_buffer, limits.output_bytes, stderr_state),
            daemon=True,
        )
        stdout_thread.start()
        stderr_thread.start()
        try:
            returncode = process.wait(timeout=limits.wall_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            subprocess.run(
                [self.docker_binary, "rm", "-f", container_name],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=15,
                check=False,
            )
            try:
                returncode = process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                returncode = process.wait(timeout=5)
        stdout_thread.join(timeout=5)
        stderr_thread.join(timeout=5)
        duration = time.monotonic() - started
        stdout = bytes(stdout_buffer).decode("utf-8", errors="replace")
        stderr = bytes(stderr_buffer).decode("utf-8", errors="replace")
        return SandboxResult(
            command=argv,
            image=image,
            returncode=returncode,
            stdout=stdout,
            stderr=stderr,
            duration_seconds=duration,
            timed_out=timed_out,
            output_truncated=stdout_state["truncated"] or stderr_state["truncated"],
            container_name=container_name,
            security_profile=security_profile,
        )

    @staticmethod
    def _drain_bounded(stream: object, buffer: bytearray, limit: int, state: dict[str, bool]) -> None:
        while True:
            chunk = stream.read(65_536)  # type: ignore[attr-defined]
            if not chunk:
                return
            remaining = limit - len(buffer)
            if remaining > 0:
                buffer.extend(chunk[:remaining])
            if len(chunk) > max(remaining, 0):
                state["truncated"] = True


def write_receipt(path: str | Path, result: SandboxResult) -> str:
    """Atomically write a tamper-evident sandbox receipt and return its hash."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = result.to_dict()
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    digest = hashlib.sha256(canonical.encode()).hexdigest()
    envelope = {"schema_version": 1, "sha256": digest, "result": payload}
    temporary = target.with_name(target.name + ".tmp")
    temporary.write_text(json.dumps(envelope, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(target)
    return digest


def write_status_receipt(path: str | Path, status: dict[str, object]) -> str:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    canonical = json.dumps(status, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    digest = hashlib.sha256(canonical.encode()).hexdigest()
    envelope = {"schema_version": 1, "sha256": digest, "status": status}
    temporary = target.with_name(target.name + ".tmp")
    temporary.write_text(json.dumps(envelope, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(target)
    return digest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="check that the Docker daemon is reachable")
    parser.add_argument("--image", help="optionally run a no-network smoke command in this digest-pinned image")
    parser.add_argument("--receipt", type=Path, help="atomically save a hash-covered status receipt")
    args = parser.parse_args(argv)
    status = docker_status()
    if args.image and status.get("ready"):
        with tempfile.TemporaryDirectory(prefix=".ouroboros-sandbox-check-", dir=Path.cwd()) as workspace:
            try:
                result = DockerSandbox().run(
                    image=args.image,
                    workspace=workspace,
                    command=("/usr/bin/env",),
                    limits=SandboxLimits(wall_seconds=30, memory_mb=128, cpus=1, pids=32, tmpfs_mb=32),
                )
                status["smoke"] = result.to_dict()
            except (OSError, ValueError, SandboxError) as exc:
                status["smoke"] = {"error": f"{type(exc).__name__}: {exc}"}
        smoke = status["smoke"]
        status["ready"] = (
            bool(status.get("ready"))
            and smoke.get("returncode") == 0
            and "OUROBOROS_SANDBOX=1" in str(smoke.get("stdout", ""))
            and "/var/run/docker.sock" not in str(smoke)
        )
    if args.receipt:
        write_status_receipt(args.receipt, status)
    print(json.dumps(status, indent=2, sort_keys=True))
    return 0 if status.get("ready") else 1


if __name__ == "__main__":
    raise SystemExit(main())
