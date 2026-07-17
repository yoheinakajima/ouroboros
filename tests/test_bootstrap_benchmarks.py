from __future__ import annotations

import unittest

from research.bootstrap_benchmarks import SOURCES
from research.swe_harbor import HARBOR_REVISION, SWEBENCH_REVISION


class BenchmarkBootstrapTests(unittest.TestCase):
    def test_local_core_sources_are_full_commit_pinned(self) -> None:
        self.assertEqual({source.name for source in SOURCES}, {"harbor", "swe", "swe_verified", "terminal2"})
        for source in SOURCES:
            self.assertEqual(len(source.revision), 40)
            int(source.revision, 16)
            self.assertTrue(source.url.startswith("https://"))

    def test_swe_harbor_materializer_uses_the_bootstrap_revisions(self) -> None:
        revisions = {source.name: source.revision for source in SOURCES}
        self.assertEqual(HARBOR_REVISION, revisions["harbor"])
        self.assertEqual(SWEBENCH_REVISION, revisions["swe"])


if __name__ == "__main__":
    unittest.main()
