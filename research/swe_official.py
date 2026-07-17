#!/usr/bin/env python3
"""Grade a Harbor-exported patch with the pinned official SWE-bench harness."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

from research.swe_harbor import IMAGE_MANIFEST, OFFICIAL_IMAGE

RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
MAX_PATCH_BYTES = 20_000_000


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def locate_harbor_patch(job_dir: Path, instance_id: str) -> Path:
    matches = sorted(job_dir.glob(f"{instance_id}__*/verifier/model.patch"))
    if len(matches) != 1:
        raise ValueError(f"expected one Harbor patch for {instance_id}, found {len(matches)}")
    path = matches[0].resolve(strict=True)
    if path.is_symlink() or not path.is_file():
        raise ValueError("Harbor patch must be a regular file")
    return path


def pinned_image(repository: Path, instance_id: str) -> str:
    images = _read(repository / IMAGE_MANIFEST).get("images", {})
    image = str(images.get(instance_id, ""))
    if not OFFICIAL_IMAGE.fullmatch(image):
        raise ValueError(f"official SWE image is not pinned: {instance_id}")
    return image


def ensure_local_image(repository: Path, instance_id: str) -> dict[str, str]:
    image = pinned_image(repository, instance_id)
    inspect = subprocess.run(
        ["docker", "image", "inspect", image, "--format", "{{.Id}}"],
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    if inspect.returncode != 0:
        subprocess.run(["docker", "pull", image], timeout=3_600, check=True)
        inspect = subprocess.run(
            ["docker", "image", "inspect", image, "--format", "{{.Id}}"],
            text=True,
            capture_output=True,
            timeout=30,
            check=True,
        )
    image_id = inspect.stdout.strip()
    if not image_id.startswith("sha256:"):
        raise RuntimeError(f"Docker returned an invalid SWE image id: {image_id}")
    local_tag = image.split("@", 1)[0] + ":latest"
    subprocess.run(["docker", "tag", image, local_tag], timeout=30, check=True)
    tagged = subprocess.run(
        ["docker", "image", "inspect", local_tag, "--format", "{{.Id}}"],
        text=True,
        capture_output=True,
        timeout=30,
        check=True,
    ).stdout.strip()
    if tagged != image_id:
        raise RuntimeError("local SWE evaluation tag does not resolve to the pinned image id")
    return {"pinned_reference": image, "local_tag": local_tag, "image_id": image_id}


def grade_patch(
    *,
    repository: Path,
    instance_id: str,
    patch_path: Path,
    run_dir: Path,
    run_id: str,
    model_name: str,
    timeout_seconds: int = 3_600,
) -> dict[str, Any]:
    if not RUN_ID.fullmatch(run_id):
        raise ValueError("run_id must be a bounded filesystem-safe identifier")
    if not RUN_ID.fullmatch(model_name):
        raise ValueError("model_name must be a bounded filesystem-safe identifier")
    selection = _read(repository / "research/selections/swe_verified.json")
    selected = {str(item) for item in selection["development"] + selection["evaluation"]}
    if instance_id not in selected:
        raise ValueError("official grading is limited to the committed SWE selection")
    patch = patch_path.resolve(strict=True)
    if patch.is_symlink() or not patch.is_file():
        raise ValueError("model patch must be a regular file")
    if patch.stat().st_size > MAX_PATCH_BYTES:
        raise ValueError(f"model patch exceeds the {MAX_PATCH_BYTES}-byte safety limit")
    if run_dir.exists() and any(run_dir.iterdir()):
        raise FileExistsError(f"official SWE run directory is not empty: {run_dir}")
    run_dir.mkdir(parents=True, exist_ok=True)

    image = ensure_local_image(repository, instance_id)
    predictions = run_dir / "predictions.json"
    predictions.write_text(
        json.dumps(
            [
                {
                    "instance_id": instance_id,
                    "model_name_or_path": model_name,
                    "model_patch": patch.read_text(encoding="utf-8"),
                }
            ],
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    python = repository / "benchmark/.cache/venvs/swebench/bin/python3"
    swe_source = repository / "benchmark/.cache/swe"
    dataset = repository / "benchmark/.cache/swe_verified/data/test-00000-of-00001.parquet"
    for required in (python, swe_source, dataset):
        if not required.exists():
            raise FileNotFoundError(required)
    command = [
        str(python),
        "-m",
        "swebench.harness.run_evaluation",
        "--dataset_name",
        str(dataset),
        "--split",
        "test",
        "--instance_ids",
        instance_id,
        "--predictions_path",
        str(predictions),
        "--max_workers",
        "1",
        "--timeout",
        str(timeout_seconds),
        "--force_rebuild",
        "false",
        "--cache_level",
        "instance",
        "--clean",
        "false",
        "--run_id",
        run_id,
        "--namespace",
        "swebench",
        "--instance_image_tag",
        "latest",
        "--report_dir",
        str(run_dir),
    ]
    environment = os.environ.copy()
    existing = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = os.pathsep.join([str(swe_source), *([existing] if existing else [])])
    completed = subprocess.run(
        command,
        cwd=run_dir,
        env=environment,
        text=True,
        capture_output=True,
        timeout=timeout_seconds + 600,
        check=False,
    )
    (run_dir / "official-evaluator.stdout.txt").write_text(completed.stdout, encoding="utf-8")
    (run_dir / "official-evaluator.stderr.txt").write_text(completed.stderr, encoding="utf-8")
    report_path = run_dir / f"{model_name}.{run_id}.json"
    if not report_path.is_file():
        raise RuntimeError(f"official SWE evaluator produced no report (exit {completed.returncode})")
    report = _read(report_path)
    resolved = instance_id in set(report.get("resolved_ids", []))
    errored = instance_id in set(report.get("error_ids", []))
    receipt = {
        "schema_version": 1,
        "suite_id": "ouro_swe_50",
        "instance_id": instance_id,
        "run_id": run_id,
        "official_evaluator_revision": selection["source_revision"],
        "dataset_revision": selection["dataset"]["revision"],
        "image": image,
        "patch_sha256": _sha256(patch),
        "report_sha256": _sha256(report_path),
        "completed": instance_id in set(report.get("completed_ids", [])),
        "resolved": resolved,
        "error": errored,
        "evaluator_exit_code": completed.returncode,
        "passed": completed.returncode == 0 and not errored,
    }
    (run_dir / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instance", required=True)
    parser.add_argument("--patch", type=Path)
    parser.add_argument("--harbor-job-dir", type=Path)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--model-name", default="gpt-5.6-sol")
    parser.add_argument("--timeout", type=int, default=3_600)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    if (args.patch is None) == (args.harbor_job_dir is None):
        parser.error("provide exactly one of --patch or --harbor-job-dir")
    patch = args.patch or locate_harbor_patch(args.harbor_job_dir.resolve(strict=True), args.instance)
    receipt = grade_patch(
        repository=args.root.resolve(),
        instance_id=args.instance,
        patch_path=patch,
        run_dir=args.run_dir.resolve(),
        run_id=args.run_id,
        model_name=args.model_name,
        timeout_seconds=args.timeout,
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
