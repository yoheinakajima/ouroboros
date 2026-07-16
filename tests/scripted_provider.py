"""Deterministic scripted LLM provider for Ouroboros tests.

Implements the ActiveGraph ``LLMProvider`` protocol and drives the builder
tool loop from a per-generation script of tool-call turns, so tests exercise
the REAL tool bodies, subprocess execution, and evaluation — only the model
is scripted. The final turn returns a structured ``BuilderFinal``.
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any, Callable, Optional

from activegraph.llm.types import LLMResponse, ToolCall

import ouroboros as ob


class ScriptError(RuntimeError):
    pass


# A "turn" is a list of (tool_name, args_dict) tuples issued together.
# A "generation script" is a list of turns ending when the builder submits.
GenerationScript = list[list[tuple[str, dict[str, Any]]]]


class ScriptedProvider:
    default_model = "scripted-model-v1"

    def __init__(
        self,
        *,
        contract: ob.ObjectiveContractModel,
        private: ob.PrivateSuiteModel,
        builder_generations: list[GenerationScript],
        judge_scores: Optional[dict[str, tuple[int, int]]] = None,
        judge_default: tuple[int, int] = (70, 70),
        builder_raise_on_gen: Optional[int] = None,
        judge_fn: Optional[Callable[[str], dict[str, tuple[int, int]]]] = None,
    ) -> None:
        self._contract = contract
        self._private = private
        self._builder_generations = builder_generations
        self._judge_scores = judge_scores or {}
        self._judge_default = judge_default
        self._builder_raise_on_gen = builder_raise_on_gen
        self._judge_fn = judge_fn
        self._builder_gen_index = -1
        self.calls: list[str] = []

    # ---- LLMProvider protocol ------------------------------------------------

    def complete(
        self,
        *,
        system: str,
        messages: list[Any],
        model: str,
        max_tokens: int,
        temperature: float,
        top_p: float,
        output_schema: Optional[type],
        timeout_seconds: float,
        tools: Optional[list[dict[str, Any]]] = None,
        structured_output_mode: str = "prompt",
    ) -> LLMResponse:
        name = getattr(output_schema, "__name__", "")
        self.calls.append(name)
        if name == "ObjectiveContractModel":
            return self._final(self._contract)
        if name == "PrivateSuiteModel":
            return self._final(self._private)
        if name == "JudgeVerdict":
            return self._judge(system, messages)
        if name == "BuilderFinal":
            return self._builder(messages)
        raise ScriptError(f"scripted provider has no program for schema {name!r}")

    def estimate_cost(self, *, input_tokens: int, output_tokens: int, model: str) -> Decimal:
        return Decimal("0")

    def count_tokens(self, *, system: str, messages: list[Any], model: str) -> int:
        return len(system) // 4 + sum(len(getattr(m, "content", "")) for m in messages) // 4

    def recognizes_model(self, name: str) -> bool:
        return True

    def supports_native_structured_output(self, model: str) -> bool:
        return False

    # ---- helpers -------------------------------------------------------------

    def _final(self, parsed: Any) -> LLMResponse:
        return LLMResponse(
            raw_text=parsed.model_dump_json() if hasattr(parsed, "model_dump_json") else "",
            parsed=parsed,
            input_tokens=10,
            output_tokens=10,
            cost_usd=Decimal("0"),
            latency_seconds=0.0,
            model=self.default_model,
            finish_reason="end_turn",
            tool_calls=None,
        )

    def _assistant_turns(self, messages: list[Any]) -> int:
        return sum(1 for m in messages if getattr(m, "role", "") == "assistant")

    def _builder(self, messages: list[Any]) -> LLMResponse:
        turn_index = self._assistant_turns(messages)
        if turn_index == 0:
            self._builder_gen_index += 1
        gen = self._builder_gen_index
        if self._builder_raise_on_gen is not None and gen == self._builder_raise_on_gen:
            raise ScriptError(f"injected builder failure at generation {gen}")
        script: GenerationScript = (
            self._builder_generations[gen]
            if gen < len(self._builder_generations)
            else []
        )
        if turn_index < len(script):
            turn = script[turn_index]
            tool_calls = [
                ToolCall(id=f"call_g{gen}_t{turn_index}_{i}", name=tname, args=targs)
                for i, (tname, targs) in enumerate(turn)
            ]
            return LLMResponse(
                raw_text="",
                parsed=None,
                input_tokens=10,
                output_tokens=10,
                cost_usd=Decimal("0"),
                latency_seconds=0.0,
                model=self.default_model,
                finish_reason="tool_use",
                tool_calls=tool_calls,
            )
        submitted = any(
            tname == "submit_candidate" for turn in script for (tname, _) in turn
        )
        return self._final(
            ob.BuilderFinal(
                summary=f"generation {gen} builder complete",
                submitted=submitted,
                notes="scripted",
            )
        )

    def _judge(self, system: str, messages: list[Any]) -> LLMResponse:
        text = "\n".join(getattr(m, "content", "") for m in messages)
        case_ids = list(dict.fromkeys(re.findall(r'"case_id":\s*"([^"]+)"', text)))
        if not case_ids:
            case_ids = list(dict.fromkeys(re.findall(r'case_id[^A-Za-z0-9_]+([A-Za-z0-9_]+)', text)))
        overrides = self._judge_fn(text) if self._judge_fn else {}
        scores = []
        for case_id in case_ids:
            a, b = overrides.get(case_id, self._judge_scores.get(case_id, self._judge_default))
            scores.append(
                ob.JudgeCaseScore(case_id=case_id, a_score=a, b_score=b, rationale="scripted")
            )
        verdict = ob.JudgeVerdict(scores=scores, summary="scripted judge verdict")
        return self._final(verdict)


# ---- scenario construction helpers ------------------------------------------


def contract(
    *,
    objective: str,
    deliverable_kind: str = "cli_app",
    public_tests: list[ob.TestCaseSpec],
    rubric: Optional[list[ob.RubricCriterion]] = None,
    required_artifacts: Optional[list[str]] = None,
    success_threshold: int = 60,
) -> ob.ObjectiveContractModel:
    rubric = rubric or [
        ob.RubricCriterion(
            id="capability",
            criterion="Does the workspace actually accomplish the objective when executed?",
            anchors="0: nothing works; 50: partially works; 100: fully works with clear output.",
        ),
        ob.RubricCriterion(
            id="robustness",
            criterion="Does it handle the specified inputs without crashing?",
            anchors="0: crashes; 50: handles the happy path; 100: handles edge cases too.",
        ),
    ]
    return ob.ObjectiveContractModel(
        objective=objective,
        deliverable_kind=deliverable_kind,
        capability_requirements=["executes", "produces structured output"],
        public_behavior_spec="The entrypoint reads JSON on stdin and writes JSON on stdout.",
        entrypoint_protocol="json-stdin -> json-stdout",
        required_artifacts=required_artifacts or [],
        public_tests=public_tests,
        qualitative_rubric=rubric,
        success_threshold=success_threshold,
        stopping_condition="all public and hidden tests pass and rubric threshold met",
    )


def private_suite(tests: list[ob.TestCaseSpec], design_notes: str = "") -> ob.PrivateSuiteModel:
    return ob.PrivateSuiteModel(private_tests=tests, design_notes=design_notes)


def write_turn(files: dict[str, str]) -> list[tuple[str, dict[str, Any]]]:
    return [("write_file", {"path": path, "content": content}) for path, content in files.items()]


def submit_turn(summary: str, evidence: str, next_strategy: str) -> list[tuple[str, dict[str, Any]]]:
    return [
        (
            "submit_candidate",
            {"summary": summary, "evidence": evidence, "next_strategy": next_strategy},
        )
    ]
