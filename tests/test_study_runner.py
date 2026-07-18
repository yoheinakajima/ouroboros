from __future__ import annotations

from pathlib import Path

from research.study_runner import (
    TaskRef,
    _opaque_sham,
    _seed,
    evaluation_tasks,
    plan,
)

ROOT = Path(__file__).resolve().parents[1]


def test_full_study_plan_has_exact_frozen_attempt_counts() -> None:
    value = plan(ROOT, replications=3)

    assert value["development_tasks_per_lineage"] == 28
    assert value["development_attempts"] == 252
    assert value["probe_tasks"] == 19
    assert value["one_replication_probe_attempts"] == 228
    assert value["full_evaluation_tasks"] == 65
    assert value["preliminary_full_attempts"] == 1170
    assert value["suites"] == {
        "ouro_activegraph_50": {"development": 2, "probe": 3, "evaluation": 3},
        "ouro_swe_50": {"development": 20, "probe": 10, "evaluation": 50},
        "ouro_terminal_12": {"development": 6, "probe": 6, "evaluation": 12},
    }


def test_probe_is_an_ordered_subset_of_every_held_out_suite() -> None:
    probe = evaluation_tasks(ROOT, probe=True)
    full = evaluation_tasks(ROOT, probe=False)

    assert len(probe) == 19
    assert set(probe) < set(full)
    for suite_id in ("ouro_swe_50", "ouro_terminal_12", "ouro_activegraph_50"):
        probe_ids = [row.task_id for row in probe if row.suite_id == suite_id]
        full_ids = [row.task_id for row in full if row.suite_id == suite_id]
        assert probe_ids == [task_id for task_id in full_ids if task_id in set(probe_ids)]


def test_seed_is_paired_across_approaches_and_changes_by_replication() -> None:
    task = TaskRef("ouro_swe_50", "django__django-17087")

    assert _seed(1, task) == _seed(1, task)
    assert _seed(1, task) != _seed(2, task)


def test_opaque_sham_has_exact_requested_length_and_is_deterministic() -> None:
    first = _opaque_sham(64_000, label="replication-1/minimal")
    second = _opaque_sham(64_000, label="replication-1/minimal")

    assert len(first.encode()) == 64_000
    assert first == second
    assert "debug" not in first
    assert "test" not in first
