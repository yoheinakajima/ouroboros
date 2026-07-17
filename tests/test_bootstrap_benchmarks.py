from __future__ import annotations

import unittest

from research.bootstrap_benchmarks import SOURCES


class BenchmarkBootstrapTests(unittest.TestCase):
    def test_local_core_sources_are_full_commit_pinned(self) -> None:
        self.assertEqual({source.name for source in SOURCES}, {"swe", "swe_verified", "terminal2"})
        for source in SOURCES:
            self.assertEqual(len(source.revision), 40)
            int(source.revision, 16)
            self.assertTrue(source.url.startswith("https://"))


if __name__ == "__main__":
    unittest.main()
