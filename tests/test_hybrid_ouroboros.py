from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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


def composed_drafts() -> tuple[PackDraft, PackDraft]:
    planner = '''from activegraph.packs import Pack, behavior

@behavior(name="plan_normalization", on=["hybrid.task.requested"])
def plan_normalization(event, graph, ctx):
    if event.payload.get("operation") != "compose":
        return
    graph.emit("hybrid.compose.planned", {
        "request_id": event.payload["request_id"],
        "words": str(event.payload.get("input", "")).strip().lower().split(),
    })

PACK = Pack(
    name="normalization_planner",
    version="1.0.0",
    description="Turns a request into a normalized intermediate event.",
    behaviors=(plan_normalization,),
)
'''
    renderer = '''from activegraph.packs import Pack, behavior

@behavior(name="render_normalization", on=["hybrid.compose.planned"])
def render_normalization(event, graph, ctx):
    graph.emit("hybrid.task.completed", {
        "request_id": event.payload["request_id"],
        "output": "-".join(event.payload["words"]),
    })

PACK = Pack(
    name="normalization_renderer",
    version="1.0.0",
    description="Completes normalized intermediate events.",
    behaviors=(render_normalization,),
)
'''
    return (
        PackDraft(
            name="normalization_planner",
            version="1.0.0",
            description="Turns a request into a normalized intermediate event.",
            files={"__init__.py": planner},
            behaviors=("plan_normalization",),
        ),
        PackDraft(
            name="normalization_renderer",
            version="1.0.0",
            description="Completes normalized intermediate events.",
            files={"__init__.py": renderer},
            behaviors=("render_normalization",),
        ),
    )


class HybridOuroborosTests(unittest.TestCase):
    def test_composed_pack_set_is_evaluated_and_adopted_as_one_atomic_unit(self):
        public = (Case("public-compose", {"operation": "compose", "input": "Hello World"}, "hello-world"),)
        private = (
            Case("private-compose", {"operation": "compose", "input": "  Recursive   Agent "}, "recursive-agent"),
        )
        with tempfile.TemporaryDirectory() as temporary:
            organism = HybridOuroboros(temporary)
            report = organism.evolve_set(
                objective="Build a composed normalization pipeline",
                drafts=composed_drafts(),
                public_cases=public,
                private_cases=private,
            )
            self.assertTrue(report.accepted, report)
            self.assertEqual(
                [item["name"] for item in report.packs],
                ["normalization_planner", "normalization_renderer"],
            )
            registry = json.loads((Path(temporary) / "registry.json").read_text())
            self.assertEqual(len(registry["adopted"]), 2)

            restarted = organism.restart()
            self.assertEqual(
                restarted.invoke({"operation": "compose", "input": "Pack Sets Compose"}),
                "pack-sets-compose",
            )
            event_types = [event.type for event in restarted.runtime.graph.events]
            self.assertEqual(event_types.count("ouroboros.hybrid.pack_set_adopted"), 1)
            self.assertEqual(event_types.count("ouroboros.hybrid.pack_adopted"), 2)

    def test_one_invalid_pack_rejects_the_entire_set_before_adoption(self):
        planner, renderer = composed_drafts()
        dangerous = PackDraft(
            name=renderer.name,
            version=renderer.version,
            description=renderer.description,
            files={"__init__.py": "import os\n" + renderer.files["__init__.py"]},
            behaviors=renderer.behaviors,
        )
        cases = (Case("compose", {"operation": "compose", "input": "Hello World"}, "hello-world"),)
        with tempfile.TemporaryDirectory() as temporary:
            report = HybridOuroboros(temporary).evolve_set(
                objective="Reject a partially unsafe set",
                drafts=(planner, dangerous),
                public_cases=cases,
                private_cases=(Case("private", {"operation": "compose", "input": "A B"}, "a-b"),),
            )
            registry = json.loads((Path(temporary) / "registry.json").read_text())
            adopted = Path(temporary) / "adopted"
        self.assertFalse(report.accepted)
        self.assertEqual(report.reason, "static policy rejected proposal")
        self.assertEqual(registry["adopted"], [])
        self.assertFalse(adopted.exists())

    def test_registry_write_failure_rolls_back_every_new_pack_directory(self):
        public = (Case("public-compose", {"operation": "compose", "input": "Hello World"}, "hello-world"),)
        private = (Case("private-compose", {"operation": "compose", "input": "A B"}, "a-b"),)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            organism = HybridOuroboros(root)
            with patch.object(organism, "_write_registry", side_effect=OSError("simulated registry failure")):
                report = organism.evolve_set(
                    objective="Rollback a composed normalization pipeline",
                    drafts=composed_drafts(),
                    public_cases=public,
                    private_cases=private,
                )
            registry = json.loads((root / "registry.json").read_text())
            adopted_files = list((root / "adopted").rglob("manifest.toml"))
        self.assertFalse(report.accepted)
        self.assertEqual(report.reason, "atomic adoption failed")
        self.assertEqual(registry["adopted"], [])
        self.assertEqual(adopted_files, [])

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
