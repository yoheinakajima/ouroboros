from __future__ import annotations

import io
import tempfile
import unittest
from pathlib import Path

from research.sandbox import DockerSandbox, SandboxLimits, SandboxResult, _safe_environment, write_receipt


class CapturingSandbox(DockerSandbox):
    def __init__(self) -> None:
        super().__init__()
        self.invocation: list[str] = []

    def _execute(self, docker_argv, **kwargs):  # type: ignore[no-untyped-def]
        self.invocation = list(docker_argv)
        return SandboxResult(
            command=kwargs["argv"],
            image=kwargs["image"],
            returncode=0,
            stdout="",
            stderr="",
            duration_seconds=0,
            timed_out=False,
            output_truncated=False,
            container_name=kwargs["container_name"],
            security_profile=kwargs["security_profile"],
        )


class DockerSandboxTests(unittest.TestCase):
    def test_command_has_the_frozen_isolation_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary).resolve()
            limits = SandboxLimits()
            command = DockerSandbox()._docker_command(
                image="example.invalid/task@sha256:" + "a" * 64,
                workspace=workspace,
                command=("python", "-V"),
                limits=limits,
                environment={"TASK_SEED": "7"},
                container_name="ouroboros-test",
                network=False,
            )
        joined = " ".join(command)
        self.assertIn("--network none", joined)
        self.assertIn("--read-only", command)
        self.assertIn("--cap-drop=ALL", command)
        self.assertIn("no-new-privileges:true", command)
        self.assertIn("65532:65532", command)
        self.assertIn("type=bind", joined)
        self.assertNotIn("/var/run/docker.sock", joined)
        self.assertEqual(command[-2:], ["python", "-V"])

    def test_images_must_be_digest_pinned(self) -> None:
        for valid in ("python@sha256:" + "1" * 64, "sha256:" + "1" * 64):
            DockerSandbox.validate_image(valid)
        for invalid in ("python:3.11", "sha256:short", "python@sha256:ABC"):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                DockerSandbox.validate_image(invalid)

    def test_grader_uses_three_separate_mounts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            grader = root / "grader"
            submission = root / "submission"
            output = root / "output"
            for path in (grader, submission, output):
                path.mkdir()
            sandbox = CapturingSandbox()
            result = sandbox.run_grader(
                image="example.invalid/grader@sha256:" + "b" * 64,
                grader_workspace=grader,
                submission=submission,
                output_workspace=output,
                command=("python", "grader.py"),
                limits=SandboxLimits(wall_seconds=1),
            )
        joined = " ".join(sandbox.invocation)
        self.assertIn(f"src={grader.resolve()},dst=/grader,readonly", joined)
        self.assertIn(f"src={submission.resolve()},dst=/submission,readonly", joined)
        self.assertIn(f"src={output.resolve()},dst=/output", joined)
        self.assertIn("--network none", joined)
        self.assertEqual(result.security_profile["submission_mount"], "/submission:ro")

    def test_credential_shaped_environment_is_rejected(self) -> None:
        self.assertEqual(_safe_environment({"TASK_SEED": "1"}), {"TASK_SEED": "1"})
        for name in ("OPENAI_API_KEY", "AUTH_TOKEN", "DB_PASSWORD"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                _safe_environment({name: "secret"})

    def test_output_drain_discards_bytes_beyond_the_limit(self) -> None:
        buffer = bytearray()
        state = {"truncated": False}
        DockerSandbox._drain_bounded(io.BytesIO(b"a" * 100), buffer, 16, state)
        self.assertEqual(buffer, b"a" * 16)
        self.assertTrue(state["truncated"])

    def test_receipt_is_hashed_and_atomic(self) -> None:
        result = SandboxResult(
            command=("python", "-V"),
            image="python@sha256:" + "1" * 64,
            returncode=0,
            stdout="Python 3.11\n",
            stderr="",
            duration_seconds=0.1,
            timed_out=False,
            output_truncated=False,
            container_name="ouroboros-test",
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "receipt.json"
            digest = write_receipt(path, result)
            text = path.read_text(encoding="utf-8")
        self.assertIn(digest, text)
        self.assertFalse(path.with_name(path.name + ".tmp").exists())


if __name__ == "__main__":
    unittest.main()
