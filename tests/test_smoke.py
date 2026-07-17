from __future__ import annotations

import unittest

from research.smoke import CALIBRATION_IMAGE, FAMILY_FIXTURES


class CalibrationSmokeTests(unittest.TestCase):
    def test_every_preregistered_family_has_a_distinct_fixture(self) -> None:
        self.assertEqual(
            set(FAMILY_FIXTURES),
            {"swe", "terminal", "mle", "rebench", "paperbench", "activegraph"},
        )
        canonical = {repr(sorted(value.items())) for value in FAMILY_FIXTURES.values()}
        self.assertEqual(len(canonical), 6)

    def test_calibration_image_is_digest_pinned(self) -> None:
        name, digest = CALIBRATION_IMAGE.split("@sha256:")
        self.assertTrue(name)
        self.assertEqual(len(digest), 64)


if __name__ == "__main__":
    unittest.main()
