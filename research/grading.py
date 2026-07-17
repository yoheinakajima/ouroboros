"""Manager-only grading in a fresh container after an agent attempt ends."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path, PurePosixPath

from pydantic import BaseModel, Field

from research.contracts import ScoreRecord
from research.sandbox import DockerSandbox, SandboxLimits, write_receipt


class GraderSpec(BaseModel):
    grader_id: str
    grader_revision: str
    image: str
    command: list[str] = Field(min_length=1)
    score_path: str = "score.json"
    minimum_score: float | None = None
    maximum_score: float | None = None
    limits: dict[str, float | int] = Field(default_factory=dict)


def _safe_relative(raw: str) -> Path:
    relative = PurePosixPath(raw)
    if relative.is_absolute() or not relative.parts or ".." in relative.parts:
        raise ValueError(f"unsafe grader-relative path: {raw!r}")
    return Path(*relative.parts)


class SealedGrader:
    def __init__(self, spec: GraderSpec, *, sandbox: DockerSandbox | None = None) -> None:
        DockerSandbox.validate_image(spec.image)
        self.spec = spec
        self.sandbox = sandbox or DockerSandbox()

    def grade(
        self,
        *,
        run_id: str,
        grader_workspace: str | Path,
        submission: str | Path,
        output_dir: str | Path,
    ) -> ScoreRecord:
        workspace = Path(grader_workspace).resolve(strict=True)
        source = Path(submission).resolve(strict=True)
        output = Path(output_dir).resolve()
        if not workspace.is_dir() or workspace.is_symlink():
            raise ValueError("grader workspace must be a real directory")
        if workspace == source or workspace in source.parents or source in workspace.parents:
            raise ValueError("submission and sealed grader workspace must be separate trees")
        if not source.is_dir() or source.is_symlink():
            raise ValueError("submission must be a real directory")
        for path in (*workspace.rglob("*"), *source.rglob("*")):
            if path.is_symlink():
                raise ValueError("sealed grader inputs may not contain symlinks")

        output.mkdir(parents=True, exist_ok=True)
        if any(output.iterdir()):
            raise FileExistsError("grader output directory must start empty")
        limits = SandboxLimits(
            wall_seconds=float(self.spec.limits.get("wall_seconds", 1_800)),
            memory_mb=int(self.spec.limits.get("memory_mb", 4_096)),
            cpus=float(self.spec.limits.get("cpus", 4)),
            pids=int(self.spec.limits.get("pids", 512)),
            tmpfs_mb=int(self.spec.limits.get("tmpfs_mb", 512)),
            output_bytes=int(self.spec.limits.get("output_bytes", 2_000_000)),
        )
        result = self.sandbox.run_grader(
            image=self.spec.image,
            grader_workspace=workspace,
            submission=source,
            output_workspace=output,
            command=tuple(self.spec.command),
            limits=limits,
            environment={"OUROBOROS_RUN_ID": run_id},
        )
        write_receipt(output / "grader_sandbox.json", result)
        if result.timed_out or result.returncode != 0:
            score = ScoreRecord(
                run_id=run_id,
                grader_id=self.spec.grader_id,
                grader_revision=self.spec.grader_revision,
                primary_score=0.0,
                grader_error=(
                    "grader timed out"
                    if result.timed_out
                    else f"grader exited {result.returncode}: {result.stderr[-2000:]}"
                ),
            )
        else:
            score_file = output / _safe_relative(self.spec.score_path)
            if not score_file.is_file() or score_file.is_symlink():
                raise ValueError("grader completed without its declared regular score file")
            score = ScoreRecord.model_validate(json.loads(score_file.read_text(encoding="utf-8")))
            if score.run_id != run_id:
                raise ValueError("grader score run_id mismatch")
            if score.grader_id != self.spec.grader_id or score.grader_revision != self.spec.grader_revision:
                raise ValueError("grader identity or revision mismatch")
            if not math.isfinite(score.primary_score):
                raise ValueError("grader returned a non-finite score")
            if self.spec.minimum_score is not None and score.primary_score < self.spec.minimum_score:
                raise ValueError("grader returned a score below the preregistered bound")
            if self.spec.maximum_score is not None and score.primary_score > self.spec.maximum_score:
                raise ValueError("grader returned a score above the preregistered bound")
        score_path = output / "score.json"
        temporary = score_path.with_name(score_path.name + ".tmp")
        temporary.write_text(score.model_dump_json(indent=2) + "\n", encoding="utf-8")
        temporary.replace(score_path)
        receipt = {
            "schema_version": 1,
            "run_id": run_id,
            "grader_id": self.spec.grader_id,
            "grader_revision": self.spec.grader_revision,
            "image": self.spec.image,
            "command": self.spec.command,
            "submission_hash": hash_tree(source),
            "score_sha256": hashlib.sha256(score_path.read_bytes()).hexdigest(),
        }
        receipt_path = output / "grader_receipt.json"
        receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return score


def hash_tree(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"symlink in sealed tree: {path}")
        if path.is_file():
            digest.update(path.relative_to(root).as_posix().encode())
            digest.update(b"\0")
            digest.update(path.read_bytes())
            digest.update(b"\0")
    return "sha256:" + digest.hexdigest()
