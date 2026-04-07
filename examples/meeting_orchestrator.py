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


def validate_meeting_payload(payload: dict[str, Any]) -> ValidationResult:
    required = ["meeting_title", "duration_minutes", "allowed_slots", "selected_slot", "required_attendees", "conflicts"]
    for field_name in required:
        if field_name not in payload:
            return ValidationResult(False, f"missing_field:{field_name}", DiscoveredConstraint(field_name, "invalid", None))

    if not isinstance(payload["duration_minutes"], int) or payload["duration_minutes"] < 15:
        return ValidationResult(False, "duration_too_short", DiscoveredConstraint("duration_minutes", "less", 15))
    if not isinstance(payload["allowed_slots"], list) or not payload["allowed_slots"]:
        return ValidationResult(False, "allowed_slots_invalid", DiscoveredConstraint("allowed_slots", "invalid", None))
    if not isinstance(payload["required_attendees"], list) or not payload["required_attendees"]:
        return ValidationResult(False, "required_attendees_invalid", DiscoveredConstraint("required_attendees", "invalid", None))
    if payload["selected_slot"] is not None and payload["selected_slot"] not in payload["allowed_slots"]:
        return ValidationResult(False, "selected_slot_out_of_bounds", DiscoveredConstraint("selected_slot", "invalid", None))
    if not isinstance(payload["conflicts"], int) or payload["conflicts"] < 0:
        return ValidationResult(False, "conflicts_invalid", DiscoveredConstraint("conflicts", "invalid", None))
    return ValidationResult(True, "valid")


def score_meeting_payload(payload: dict[str, Any]) -> float:
    slot_selected = 1.0 if payload.get("selected_slot") else 0.0
    conflicts = int(payload.get("conflicts", 99))
    conflict_score = max(0.0, 1.0 - (conflicts * 0.25))
    allowed_slots_score = min(len(payload.get("allowed_slots", [])) / 4.0, 1.0)
    return round((0.55 * conflict_score) + (0.30 * slot_selected) + (0.15 * allowed_slots_score), 4)


def orchestrator_proposal_generator(store: EngineStore) -> Proposal:
    state = store.current_state()
    payload = copy.deepcopy(state.payload)
    mode: ProposalMode = "explore" if store.run.stagnation_mode == "exploration" else "improve"

    if payload["selected_slot"] != "2026-04-08T15:00:00Z":
        delta = {"selected_slot": "2026-04-08T15:00:00Z", "conflicts": 0}
        label = "select_best_slot"
    elif "2026-04-08T15:00:00Z" in payload["allowed_slots"] and len(payload["allowed_slots"]) > 1:
        delta = {"allowed_slots": ["2026-04-08T15:00:00Z"]}
        label = "shrink_options"
    else:
        delta = {"conflicts": max(0, payload["conflicts"] - 1)}
        label = "reduce_conflicts"

    return Proposal(
        proposal_id=f"proposal_{state.state_version:04d}_{label}_{mode}",
        run_id=store.run.run_id,
        based_on_state_version=state.state_version,
        mode=mode,
        delta_type="patch",
        delta=delta,
    )


def build_meeting_engine() -> ConvergenceEngineV1Lite:
    initial_payload = {
        "meeting_title": "Agentic Orchestrator Planning Session",
        "duration_minutes": 30,
        "allowed_slots": [
            "2026-04-08T09:00:00Z",
            "2026-04-08T15:00:00Z",
            "2026-04-09T11:00:00Z"
        ],
        "selected_slot": None,
        "required_attendees": ["ops-agent", "facilitator-agent", "human-owner"],
        "conflicts": 2
    }
    return ConvergenceEngineV1Lite.initialize(
        initial_payload=initial_payload,
        validator=validate_meeting_payload,
        scorer=score_meeting_payload,
        threshold=0.50,
        exploration_floor=0.35,
        allow_equal=False,
        success_threshold=0.95,
        n1=2,
        n2=5,
        max_iterations=10,
        run_id="meeting_orchestrator_demo",
    )


if __name__ == "__main__":
    engine = build_meeting_engine()
    engine.run_until_stop(orchestrator_proposal_generator)
    print(json.dumps(engine.store.best_state().payload, indent=2, ensure_ascii=False))
