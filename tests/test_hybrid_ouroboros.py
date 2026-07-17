from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from activegraph import Graph  # noqa: E402
from activegraph.packs.manifest import PackManifestError  # noqa: E402

from experiments.hybrid_ouroboros import (  # noqa: E402
    Case,
    HybridOuroboros,
    PackDraft,
    demo_draft,
    evaluate_graph_assertions,
)

PUBLIC = (
    Case("public-basic", {"operation": "slugify", "input": "Hello World"}, "hello-world"),
    Case("public-symbols", {"operation": "slugify", "input": "Agent / Graph"}, "agent-graph"),
)
PRIVATE = (
    Case("private-spacing", {"operation": "slugify", "input": "  Recursive   Agent  "}, "recursive-agent"),
    Case("private-punctuation", {"operation": "slugify", "input": "Simple, Powerful!"}, "simple-powerful"),
)


class HybridOuroborosTests(unittest.TestCase):
    def test_graph_assertions_address_relations_by_logical_object_selectors(self):
        graph = Graph(run_id="assertion_test")
        dependent = graph.add_object("workflow_task", {"task_id": "ship", "status": "pending"})
        prerequisite = graph.add_object("workflow_task", {"task_id": "build", "status": "done"})
        graph.add_relation(dependent.id, prerequisite.id, "depends_on", {"required": True})
        evidence = evaluate_graph_assertions(
            graph,
            {
                "objects": [
                    {
                        "type": "workflow_task",
                        "where": {"task_id": "ship"},
                        "data": {"status": "pending"},
                        "version": 1,
                    }
                ],
                "relations": [
                    {
                        "type": "depends_on",
                        "source": {"type": "workflow_task", "where": {"task_id": "ship"}},
                        "target": {"type": "workflow_task", "where": {"task_id": "build"}},
                        "data": {"required": True},
                    }
                ],
                "object_type_counts": {"workflow_task": 2},
                "relation_type_counts": {"depends_on": 1},
            },
        )
        self.assertTrue(evidence["all_passed"], evidence)

    def test_adoption_restart_and_transfer_are_activegraph_native(self):
        with tempfile.TemporaryDirectory() as temporary:
            organism = HybridOuroboros(temporary)
            report = organism.evolve(
                objective="Learn a reusable slugification capability",
                draft=demo_draft(),
                public_cases=PUBLIC,
                private_cases=PRIVATE,
            )

            self.assertTrue(report.accepted, report)
            self.assertEqual(report.public_candidate, "2/2")
            self.assertEqual(report.private_candidate, "2/2")
            self.assertEqual(organism.runtime.loaded_packs(), [])

            restarted = organism.restart()
            self.assertEqual(restarted.identity()["loaded"], ["slugify_capability@1.0.0"])
            self.assertEqual(
                restarted.invoke({"operation": "slugify", "input": "Evolve / Forever"}),
                "evolve-forever",
            )
            event_types = [event.type for event in restarted.runtime.graph.events]
            self.assertIn("ouroboros.hybrid.pack_adopted", event_types)
            self.assertIn("pack.loaded", event_types)
            self.assertIn("hybrid.task.completed", event_types)

    def test_private_cases_are_manager_persisted_but_publicly_redacted(self):
        private_secret = "OURO_PRIVATE_SHOULD_NOT_PERSIST_4971"
        private = (
            Case(
                "private-secret",
                {"operation": "slugify", "input": private_secret},
                "ouro-private-should-not-persist-4971",
            ),
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            report = HybridOuroboros(root).evolve(
                objective="Learn slugification without seeing manager-private cases",
                draft=demo_draft(),
                public_cases=PUBLIC,
                private_cases=private,
            )
            self.assertTrue(report.accepted, report)
            manager_hits = 0
            for path in root.rglob("*"):
                if path.is_file():
                    if "manager" in path.relative_to(root).parts:
                        manager_hits += int(private_secret.encode() in path.read_bytes())
                    else:
                        self.assertNotIn(private_secret.encode(), path.read_bytes(), path)
            self.assertGreater(manager_hits, 0)

    def test_static_policy_rejects_authority_expansion_before_import(self):
        dangerous = demo_draft().files["__init__.py"].replace(
            "import re", "import os\nimport re\nos.environ['HYBRID_WAS_IMPORTED'] = 'yes'"
        )
        draft = PackDraft(
            name="dangerous_pack",
            version="1.0.0",
            description="Attempts ambient authority expansion.",
            files={"__init__.py": dangerous.replace('name="slugify_capability"', 'name="dangerous_pack"')},
            behaviors=("slugify",),
        )
        with tempfile.TemporaryDirectory() as temporary:
            organism = HybridOuroboros(temporary)
            report = organism.evolve(
                objective="Test the release membrane",
                draft=draft,
                public_cases=PUBLIC,
                private_cases=PRIVATE,
            )
            self.assertFalse(report.accepted)
            self.assertEqual(report.reason, "static policy rejected proposal")
            self.assertNotIn("HYBRID_WAS_IMPORTED", __import__("os").environ)
            self.assertEqual(json.loads((Path(temporary) / "registry.json").read_text())["adopted"], [])

    def test_static_policy_allows_submodules_of_an_allowed_standard_library_root(self):
        source = demo_draft().files["__init__.py"].replace("import re", "import collections.abc\nimport re")
        draft = PackDraft(
            name="stdlib_submodule",
            version="1.0.0",
            description="Uses a submodule of an explicitly allowed standard-library root.",
            files={"__init__.py": source.replace('name="slugify_capability"', 'name="stdlib_submodule"')},
            behaviors=("slugify",),
        )
        with tempfile.TemporaryDirectory() as temporary:
            report = HybridOuroboros(temporary).evolve(
                objective="Allow a safe standard-library submodule",
                draft=draft,
                public_cases=PUBLIC,
                private_cases=PRIVATE,
            )
            self.assertTrue(report.accepted, report)

    def test_private_failure_blocks_adoption_with_real_scores(self):
        weak_source = demo_draft().files["__init__.py"].replace(
            'value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")',
            'value = value.strip("-")',
        )
        weak = PackDraft(
            name="slugify_capability",
            version="1.0.0",
            description="An incomplete slugification behavior.",
            files={"__init__.py": weak_source.replace(
                'description="Adds a reusable slugification behavior."',
                'description="An incomplete slugification behavior."',
            )},
            behaviors=("slugify",),
        )
        public = (Case("public-lower", {"operation": "slugify", "input": "HELLO"}, "hello"),)
        private = (Case("private-space", {"operation": "slugify", "input": "hello world"}, "hello-world"),)
        with tempfile.TemporaryDirectory() as temporary:
            report = HybridOuroboros(temporary).evolve(
                objective="Learn complete slugification",
                draft=weak,
                public_cases=public,
                private_cases=private,
            )
            self.assertFalse(report.accepted)
            self.assertEqual(report.public_candidate, "1/1")
            self.assertEqual(report.private_candidate, "0/1")
            self.assertEqual(report.reason, "candidate did not pass every public and private case")

    def test_hash_pin_detects_adopted_pack_tampering_on_restart(self):
        with tempfile.TemporaryDirectory() as temporary:
            organism = HybridOuroboros(temporary)
            report = organism.evolve(
                objective="Learn a reusable slugification capability",
                draft=demo_draft(),
                public_cases=PUBLIC,
                private_cases=PRIVATE,
            )
            self.assertTrue(report.accepted, report)
            registry = json.loads((Path(temporary) / "registry.json").read_text())
            source = Path(temporary) / registry["adopted"][0]["path"] / "__init__.py"
            source.write_text(source.read_text() + "\n# tampered\n", encoding="utf-8")
            with self.assertRaises(PackManifestError):
                organism.restart()


if __name__ == "__main__":
    unittest.main()
