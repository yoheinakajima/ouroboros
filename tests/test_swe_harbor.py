from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from research.swe_harbor import PATCH_EXPORT_VERIFIER, _harden_task, verify_materialized


class SWEHarborHardeningTests(unittest.TestCase):
    def test_hardening_pins_base_and_removes_networked_verifier(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "environment").mkdir()
            (root / "tests").mkdir()
            (root / "environment/Dockerfile").write_text(
                "FROM mutable:latest\nRUN curl https://example.invalid/install.sh | sh\n"
            )
            (root / "tests/test.sh").write_text("uv run parser.py\n")
            (root / "task.toml").write_text(
                '[verifier]\nnetwork_mode = "public"\n[agent]\nnetwork_mode = "public"\n'
            )

            image = "swebench/example@sha256:" + "a" * 64
            _harden_task(root, instance_id="example", image=image)

            dockerfile = (root / "environment/Dockerfile").read_text()
            self.assertEqual(dockerfile, f"FROM {image}\n\nWORKDIR /testbed\nRUN mkdir -p /logs\n")
            self.assertNotIn("curl", dockerfile)
            self.assertEqual((root / "tests/test.sh").read_text(), PATCH_EXPORT_VERIFIER)
            task = (root / "task.toml").read_text()
            self.assertIn('[verifier]\nnetwork_mode = "no-network"', task)
            self.assertIn('[agent]\nnetwork_mode = "public"', task)

    def test_hardening_rejects_mutable_image(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "not digest pinned"):
                _harden_task(Path(temporary), instance_id="example", image="swebench/example:latest")
            with self.assertRaisesRegex(ValueError, "not digest pinned"):
                _harden_task(Path(temporary), instance_id="example", image="swebench/example@sha256:abc")

    def test_repository_image_manifest_pins_every_selected_task(self) -> None:
        import json

        root = Path(__file__).resolve().parents[1]
        selection = json.loads((root / "research/selections/swe_verified.json").read_text())
        images = json.loads((root / selection["official_images"]["path"]).read_text())
        selected = set(selection["development"] + selection["evaluation"])
        self.assertEqual(set(images["images"]), selected)
        self.assertTrue(all("@sha256:" in value for value in images["images"].values()))

    def test_materialized_verification_detects_drift(self) -> None:
        import json

        repository = Path(__file__).resolve().parents[1]
        selection = json.loads((repository / "research/selections/swe_verified.json").read_text())
        instance_id = selection["development"][0]
        images = json.loads((repository / selection["official_images"]["path"]).read_text())["images"]
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            task = output / instance_id
            (task / "environment").mkdir(parents=True)
            (task / "tests").mkdir()
            (task / "environment/Dockerfile").write_text("FROM mutable:latest\n")
            (task / "tests/test.sh").write_text("exit 0\n")
            (task / "task.toml").write_text('[verifier]\nnetwork_mode = "public"\n')
            failed = verify_materialized(repository=repository, output=output, task_ids=[instance_id])
            self.assertFalse(failed["passed"])

            _harden_task(task, instance_id=instance_id, image=images[instance_id])
            passed = verify_materialized(repository=repository, output=output, task_ids=[instance_id])
            self.assertTrue(passed["passed"], passed)


if __name__ == "__main__":
    unittest.main()
