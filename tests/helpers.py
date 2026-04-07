from __future__ import annotations

import copy
import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from convergence_engine import ConvergenceEngineV1Lite, Proposal
from convergence_engine.utils import canonical_json, payload_hash
from examples.spec_refinement import score_spec_payload, validate_spec_payload


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas" / "v1-lite"


def base_initial_payload() -> dict[str, Any]:
    return {
        "title": "Spec",
        "problem": "Users struggle to understand what the product does.",
        "solution": "We should improve it.",
        "budget": 18000,
        "compliance": True,
    }


def build_engine(
    *,
    allow_equal: bool = False,
    threshold: float = 0.55,
    exploration_floor: float = 0.40,
    success_threshold: float = 0.90,
    n1: int = 3,
    n2: int = 6,
    max_iterations: int = 12,
    run_id: str = "run_test",
) -> ConvergenceEngineV1Lite:
    return ConvergenceEngineV1Lite.initialize(
        initial_payload=base_initial_payload(),
        validator=validate_spec_payload,
        scorer=score_spec_payload,
        threshold=threshold,
        exploration_floor=exploration_floor,
        allow_equal=allow_equal,
        success_threshold=success_threshold,
        n1=n1,
        n2=n2,
        max_iterations=max_iterations,
        run_id=run_id,
    )


def make_proposal(
    engine: ConvergenceEngineV1Lite,
    *,
    proposal_id: str,
    delta: dict[str, Any],
    based_on_state_version: int | None = None,
    mode: str = "improve",
    delta_type: str = "patch",
) -> Proposal:
    return Proposal(
        proposal_id=proposal_id,
        run_id=engine.store.run.run_id,
        based_on_state_version=(
            engine.store.current_state().state_version
            if based_on_state_version is None
            else based_on_state_version
        ),
        mode=mode,
        delta_type=delta_type,
        delta=delta,
    )


def accepted_improvement_proposal(
    engine: ConvergenceEngineV1Lite,
    *,
    proposal_id: str = "proposal_improve",
) -> Proposal:
    return make_proposal(
        engine,
        proposal_id=proposal_id,
        delta={
            "problem": (
                engine.store.current_state().payload["problem"]
                + " Added detail for progress and a clear articulation of business impact."
            ),
        },
    )


def load_schema(name: str) -> dict[str, Any]:
    return json.loads((SCHEMA_DIR / f"{name}.schema.json").read_text())


def to_plain(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    return value


def serialize_run(engine: ConvergenceEngineV1Lite) -> dict[str, Any]:
    return {
        "run": asdict(engine.store.run),
        "states": [asdict(state) for state in engine.store.states],
        "proposals": [asdict(proposal) for proposal in engine.store.proposals],
        "constraints": [asdict(item) for item in engine.store.constraints],
        "trail": [asdict(item) for item in engine.store.trail],
        "evaluations": [asdict(item) for item in engine.store.evaluations],
    }


def assert_matches_schema_shape(testcase: Any, value: Any, schema: dict[str, Any]) -> None:
    value = to_plain(value)
    testcase.assertIsInstance(value, dict)

    required = schema.get("required", [])
    for key in required:
        testcase.assertIn(key, value)

    properties = schema.get("properties", {})
    if schema.get("additionalProperties") is False:
        testcase.assertEqual(set(properties), set(value))

    for key, subschema in properties.items():
        if key in value:
            _assert_subschema(testcase, value[key], subschema)


def _assert_subschema(testcase: Any, value: Any, schema: dict[str, Any]) -> None:
    if "oneOf" in schema:
        last_error: AssertionError | None = None
        for option in schema["oneOf"]:
            try:
                _assert_subschema(testcase, value, option)
                return
            except AssertionError as exc:
                last_error = exc
        if last_error is None:
            raise AssertionError("oneOf schema had no options")
        raise last_error

    expected_type = schema.get("type")
    if expected_type == "object":
        testcase.assertIsInstance(value, dict)
        required = schema.get("required", [])
        for key in required:
            testcase.assertIn(key, value)
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            testcase.assertTrue(set(value).issubset(set(properties)))
        for key, subschema in properties.items():
            if key in value:
                _assert_subschema(testcase, value[key], subschema)
        return

    if expected_type == "string":
        testcase.assertIsInstance(value, str)
    elif expected_type == "integer":
        testcase.assertIsInstance(value, int)
        testcase.assertNotIsInstance(value, bool)
    elif expected_type == "number":
        testcase.assertIsInstance(value, (int, float))
        testcase.assertNotIsInstance(value, bool)
    elif expected_type == "boolean":
        testcase.assertIsInstance(value, bool)
    elif expected_type == "array":
        testcase.assertIsInstance(value, list)
    elif expected_type == "null":
        testcase.assertIsNone(value)

    if "enum" in schema:
        testcase.assertIn(value, schema["enum"])
    if "minimum" in schema and value is not None:
        testcase.assertGreaterEqual(value, schema["minimum"])


def assert_state_hash_matches_payload(testcase: Any, engine: ConvergenceEngineV1Lite) -> None:
    state = engine.store.current_state()
    testcase.assertEqual(payload_hash(state.payload), state.state_hash)


def assert_run_is_deterministic(testcase: Any, left: ConvergenceEngineV1Lite, right: ConvergenceEngineV1Lite) -> None:
    testcase.assertEqual(
        canonical_json(serialize_run(left)),
        canonical_json(serialize_run(right)),
    )


def deepcopy_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return copy.deepcopy(payload)
