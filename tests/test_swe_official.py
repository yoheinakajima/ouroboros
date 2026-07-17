from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from research.swe_official import MAX_PATCH_BYTES, grade_patch, locate_harbor_patch, pinned_image


class SWEOfficialTests(unittest.TestCase):
    def test_locates_exactly_one_regular_harbor_patch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            patch = root / "task__abc/verifier/model.patch"
            patch.parent.mkdir(parents=True)
            patch.write_text("diff --git a/a b/a\n")
            self.assertEqual(locate_harbor_patch(root, "task"), patch.resolve())

    def test_duplicate_harbor_patches_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for suffix in ("a", "b"):
                patch = root / f"task__{suffix}/verifier/model.patch"
                patch.parent.mkdir(parents=True)
                patch.write_text("")
            with self.assertRaisesRegex(ValueError, "found 2"):
                locate_harbor_patch(root, "task")

    def test_selected_image_is_digest_pinned(self) -> None:
        root = Path(__file__).resolve().parents[1]
        image = pinned_image(root, "matplotlib__matplotlib-25960")
        self.assertIn("@sha256:", image)

    def test_oversized_patch_is_rejected_before_docker(self) -> None:
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temporary:
            patch = Path(temporary) / "model.patch"
            patch.write_bytes(b"x" * (MAX_PATCH_BYTES + 1))
            with self.assertRaisesRegex(ValueError, "safety limit"):
                grade_patch(
                    repository=root,
                    instance_id="matplotlib__matplotlib-25960",
                    patch_path=patch,
                    run_dir=Path(temporary) / "run",
                    run_id="test-run",
                    model_name="test-model",
                )


if __name__ == "__main__":
    unittest.main()
