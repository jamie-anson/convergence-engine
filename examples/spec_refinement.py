from __future__ import annotations

import copy
import json
from typing import Any

from convergence_engine import (
    ConvergenceEngineV1Lite,
    DiscoveredConstraint,
    EngineStore,
    Proposal,
    ProposalMode,
    ValidationResult,
)


def validate_spec_payload(payload: dict[str, Any]) -> ValidationResult:
    required_top = ["title", "problem", "solution", "budget", "compliance"]
    for field_name in required_top:
        if field_name not in payload:
            return ValidationResult(
                valid=False,
                reason=f"missing_field:{field_name}",
                discovered_constraint=DiscoveredConstraint(
                    field=field_name,
                    operator="invalid",
                    value=None,
                ),
            )

    if not isinstance(payload["title"], str) or not payload["title"].strip():
        return ValidationResult(False, "invalid_title", DiscoveredConstraint("title", "invalid", None))
    if not isinstance(payload["problem"], str) or len(payload["problem"].strip()) < 20:
        return ValidationResult(False, "problem_too_short", DiscoveredConstraint("problem", "invalid", None))
    if not isinstance(payload["solution"], str) or len(payload["solution"].strip()) < 20:
        return ValidationResult(False, "solution_too_short", DiscoveredConstraint("solution", "invalid", None))
    if not isinstance(payload["budget"], (int, float)):
        return ValidationResult(False, "budget_not_numeric", DiscoveredConstraint("budget", "invalid", None))
    if payload["budget"] <= 0:
        return ValidationResult(False, "budget_must_be_positive", DiscoveredConstraint("budget", "greater", 0))
    if payload["compliance"] is not True:
        return ValidationResult(False, "compliance_required", DiscoveredConstraint("compliance", "equals", False))
    return ValidationResult(valid=True, reason="valid")


def score_spec_payload(payload: dict[str, Any]) -> float:
    problem_len = min(len(payload.get("problem", "").strip()) / 120.0, 1.0)
    solution_len = min(len(payload.get("solution", "").strip()) / 120.0, 1.0)
    title_quality = 1.0 if len(payload.get("title", "").strip()) >= 8 else 0.3

    budget = float(payload.get("budget", 0))
    if budget <= 5000:
        budget_score = 1.0
    elif budget <= 10000:
        budget_score = 0.7
    elif budget <= 20000:
        budget_score = 0.4
    else:
        budget_score = 0.1

    compliance_score = 1.0 if payload.get("compliance") is True else 0.0
    score = (
        0.2 * title_quality
        + 0.25 * problem_len
        + 0.25 * solution_len
        + 0.15 * budget_score
        + 0.15 * compliance_score
    )
    return round(score, 4)


def deterministic_demo_proposal_generator(store: EngineStore) -> Proposal:
    state = store.current_state()
    payload = copy.deepcopy(state.payload)
    mode: ProposalMode = "explore" if store.run.stagnation_mode == "exploration" else "improve"

    problem_len = len(payload.get("problem", "").strip())
    solution_len = len(payload.get("solution", "").strip())

    if len(payload.get("title", "").strip()) < 8:
        delta = {"title": "Refined Product Specification"}
        label = "title"
    elif problem_len < 120:
        delta = {
            "problem": payload.get("problem", "").strip()
            + " This document explains the user pain clearly and anchors the business need."
        }
        label = "problem"
    elif payload.get("budget", 999999) > 10000:
        delta = {"budget": 9500}
        label = "budget"
    elif solution_len < 120:
        delta = {
            "solution": payload.get("solution", "").strip()
            + " The proposed workflow is specific, practical, and measurable for delivery."
        }
        label = "solution"
    else:
        delta = {
            "solution": payload.get("solution", "").strip()
            + " It also defines acceptance criteria and implementation boundaries."
        }
        label = "solution_refine"

    return Proposal(
        proposal_id=f"proposal_{state.state_version:04d}_{label}_{mode}",
        run_id=store.run.run_id,
        based_on_state_version=state.state_version,
        mode=mode,
        delta_type="patch",
        delta=delta,
    )


def build_demo_engine() -> ConvergenceEngineV1Lite:
    initial_payload = {
        "title": "Spec",
        "problem": "Users struggle to understand what the product does.",
        "solution": "We should improve it.",
        "budget": 18000,
        "compliance": True,
    }
    return ConvergenceEngineV1Lite.initialize(
        initial_payload=initial_payload,
        validator=validate_spec_payload,
        scorer=score_spec_payload,
        threshold=0.55,
        exploration_floor=0.40,
        allow_equal=False,
        success_threshold=0.90,
        n1=3,
        n2=6,
        max_iterations=12,
        run_id="spec_refinement_demo",
    )


if __name__ == "__main__":
    engine = build_demo_engine()
    engine.run_until_stop(deterministic_demo_proposal_generator)
    print(json.dumps(engine.store.best_state().payload, indent=2, ensure_ascii=False))
