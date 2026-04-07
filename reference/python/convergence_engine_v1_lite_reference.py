from __future__ import annotations

import copy
import hashlib
import json
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple


# ============================================================
# Convergence Engine v1-lite Reference Implementation
# ============================================================
# This implementation follows the locked v1-lite spec:
# - single score
# - single branch
# - deterministic transition
# - deterministic evaluation order
# - structured informative rejection -> structured constraint
# - oscillation protection via accepted-state hashes
#
# The engine itself is domain-agnostic.
# You provide:
# - payload validator
# - score function
# - optional proposal generator
#
# Patch semantics for delta_type="patch": JSON Merge Patch (RFC 7396)
# ============================================================

ProposalOutcome = Literal["accept", "reject_informative", "reject", "stale"]
StagnationMode = Literal["local", "exploration", "halted"]
DeltaType = Literal["patch", "replace"]
ProposalMode = Literal["improve", "explore"]
ConstraintOperator = Literal["equals", "not_equals", "greater", "less", "invalid"]


# -----------------------------
# Utility helpers
# -----------------------------

def make_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def payload_hash(payload: Dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def get_path(payload: Dict[str, Any], path: str) -> Any:
    """Simple dotted path lookup. Example: 'sections.compliance.required'"""
    current: Any = payload
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(path)
        current = current[part]
    return current


def set_path(payload: Dict[str, Any], path: str, value: Any) -> None:
    current = payload
    parts = path.split(".")
    for part in parts[:-1]:
        if part not in current or not isinstance(current[part], dict):
            current[part] = {}
        current = current[part]
    current[parts[-1]] = value


def merge_patch(target: Any, patch: Any) -> Any:
    """RFC 7396 JSON Merge Patch."""
    if not isinstance(patch, dict):
        return copy.deepcopy(patch)

    if not isinstance(target, dict):
        target = {}
    else:
        target = copy.deepcopy(target)

    for key, value in patch.items():
        if value is None:
            target.pop(key, None)
        else:
            target[key] = merge_patch(target.get(key), value)
    return target


# -----------------------------
# Schema-shaped data classes
# -----------------------------

@dataclass
class AcceptanceConfig:
    threshold: float
    exploration_floor: float
    allow_equal: bool
    success_threshold: float


@dataclass
class StagnationConfig:
    n1: int
    n2: int


@dataclass
class EngineRun:
    run_id: str
    status: Literal["active", "converged", "halted"]
    state_version: int
    best_state_version: int
    iteration: int
    max_iterations: int
    stagnation_mode: StagnationMode
    no_improve_count: int
    acceptance: AcceptanceConfig
    stagnation: StagnationConfig


@dataclass
class State:
    run_id: str
    state_version: int
    payload: Dict[str, Any]
    score: float
    state_hash: str


@dataclass
class Proposal:
    proposal_id: str
    run_id: str
    based_on_state_version: int
    mode: ProposalMode
    delta_type: DeltaType
    delta: Dict[str, Any]


@dataclass
class DiscoveredConstraint:
    field: str
    operator: ConstraintOperator
    value: Any


@dataclass
class Constraint:
    constraint_id: str
    run_id: str
    field: str
    operator: ConstraintOperator
    value: Any
    state_version: int


@dataclass
class Evaluation:
    evaluation_id: str
    proposal_id: str
    state_version: int
    outcome: ProposalOutcome
    score: float
    reason: str
    discovered_constraint: Optional[DiscoveredConstraint]


@dataclass
class TrailEntry:
    trail_id: str
    proposal_id: str
    from_state: int
    to_state: int


@dataclass
class ValidationResult:
    valid: bool
    reason: str
    discovered_constraint: Optional[DiscoveredConstraint] = None


# -----------------------------
# Engine storage
# -----------------------------

@dataclass
class EngineStore:
    run: EngineRun
    states: List[State] = field(default_factory=list)
    proposals: List[Proposal] = field(default_factory=list)
    evaluations: List[Evaluation] = field(default_factory=list)
    constraints: List[Constraint] = field(default_factory=list)
    trail: List[TrailEntry] = field(default_factory=list)
    accepted_hashes: set[str] = field(default_factory=set)

    def current_state(self) -> State:
        return self.states[-1]

    def best_state(self) -> State:
        return self.states[self.run.best_state_version]


# -----------------------------
# Engine implementation
# -----------------------------

ValidatorFn = Callable[[Dict[str, Any]], ValidationResult]
ScoreFn = Callable[[Dict[str, Any]], float]
ProposalGeneratorFn = Callable[[EngineStore], Proposal]


class ConvergenceEngineV1Lite:
    def __init__(self, store: EngineStore, validator: ValidatorFn, scorer: ScoreFn):
        self.store = store
        self.validator = validator
        self.scorer = scorer

    @classmethod
    def initialize(
        cls,
        initial_payload: Dict[str, Any],
        validator: ValidatorFn,
        scorer: ScoreFn,
        *,
        threshold: float,
        exploration_floor: float,
        allow_equal: bool,
        success_threshold: float,
        n1: int,
        n2: int,
        max_iterations: int,
        run_id: Optional[str] = None,
    ) -> "ConvergenceEngineV1Lite":
        run_id = run_id or make_id("run")

        validation = validator(copy.deepcopy(initial_payload))
        if not validation.valid:
            raise ValueError(f"Initial payload is invalid: {validation.reason}")

        initial_score = scorer(copy.deepcopy(initial_payload))
        initial_state = State(
            run_id=run_id,
            state_version=0,
            payload=copy.deepcopy(initial_payload),
            score=initial_score,
            state_hash=payload_hash(initial_payload),
        )

        run = EngineRun(
            run_id=run_id,
            status="active",
            state_version=0,
            best_state_version=0,
            iteration=0,
            max_iterations=max_iterations,
            stagnation_mode="local",
            no_improve_count=0,
            acceptance=AcceptanceConfig(
                threshold=threshold,
                exploration_floor=exploration_floor,
                allow_equal=allow_equal,
                success_threshold=success_threshold,
            ),
            stagnation=StagnationConfig(n1=n1, n2=n2),
        )

        store = EngineStore(
            run=run,
            states=[initial_state],
            accepted_hashes={initial_state.state_hash},
        )
        return cls(store=store, validator=validator, scorer=scorer)

    # -----------------------------
    # Main execution steps
    # -----------------------------

    def step(self, proposal: Proposal) -> Evaluation:
        if self.store.run.status != "active":
            raise RuntimeError(f"Engine is not active: {self.store.run.status}")

        current_state = self.store.current_state()
        self.store.proposals.append(proposal)

        # Step 1 - stale check
        if proposal.based_on_state_version != current_state.state_version:
            evaluation = Evaluation(
                evaluation_id=make_id("eval"),
                proposal_id=proposal.proposal_id,
                state_version=current_state.state_version,
                outcome="stale",
                score=current_state.score,
                reason="stale_proposal",
                discovered_constraint=None,
            )
            self._record_evaluation_and_counters(
                evaluation,
                current_score=current_state.score,
                new_score=current_state.score,
            )
            return evaluation

        # Step 2 - apply transition
        new_payload = self._transition(current_state.payload, proposal)

        # Step 3 - schema validation
        schema_validation = self.validator(copy.deepcopy(new_payload))
        if not schema_validation.valid:
            evaluation = Evaluation(
                evaluation_id=make_id("eval"),
                proposal_id=proposal.proposal_id,
                state_version=current_state.state_version,
                outcome="reject_informative",
                score=current_state.score,
                reason=schema_validation.reason,
                discovered_constraint=schema_validation.discovered_constraint,
            )
            self._record_rejection(evaluation)
            self._record_evaluation_and_counters(
                evaluation,
                current_score=current_state.score,
                new_score=current_state.score,
            )
            return evaluation

        # Step 4 - constraint validation
        constraint_failure = self._check_constraints(new_payload, current_state.state_version)
        if constraint_failure is not None:
            evaluation = Evaluation(
                evaluation_id=make_id("eval"),
                proposal_id=proposal.proposal_id,
                state_version=current_state.state_version,
                outcome="reject_informative",
                score=current_state.score,
                reason=constraint_failure.reason,
                discovered_constraint=constraint_failure.discovered_constraint,
            )
            self._record_rejection(evaluation)
            self._record_evaluation_and_counters(
                evaluation,
                current_score=current_state.score,
                new_score=current_state.score,
            )
            return evaluation

        # Step 5 - compute score/hash
        new_score = self.scorer(copy.deepcopy(new_payload))
        new_hash = payload_hash(new_payload)

        # Step 6 - oscillation protection
        if new_hash in self.store.accepted_hashes:
            evaluation = Evaluation(
                evaluation_id=make_id("eval"),
                proposal_id=proposal.proposal_id,
                state_version=current_state.state_version,
                outcome="reject",
                score=new_score,
                reason="oscillation_detected",
                discovered_constraint=None,
            )
            self._record_evaluation_and_counters(
                evaluation,
                current_score=current_state.score,
                new_score=new_score,
            )
            return evaluation

        # Step 7 - acceptance decision
        outcome, reason = self._decide_acceptance(
            current_score=current_state.score,
            new_score=new_score,
            mode=self.store.run.stagnation_mode,
        )

        evaluation = Evaluation(
            evaluation_id=make_id("eval"),
            proposal_id=proposal.proposal_id,
            state_version=current_state.state_version,
            outcome=outcome,
            score=new_score,
            reason=reason,
            discovered_constraint=None,
        )

        if outcome == "accept":
            self._persist_accept(
                proposal=proposal,
                current_state=current_state,
                new_payload=new_payload,
                new_score=new_score,
                new_hash=new_hash,
            )

        self._record_evaluation_and_counters(
            evaluation,
            current_score=current_state.score,
            new_score=new_score,
        )
        return evaluation

    def run_until_stop(self, proposal_generator: ProposalGeneratorFn) -> EngineStore:
        while self.store.run.status == "active":
            proposal = proposal_generator(self.store)
            self.step(proposal)
        return self.store

    # -----------------------------
    # Internals
    # -----------------------------

    def _transition(self, current_payload: Dict[str, Any], proposal: Proposal) -> Dict[str, Any]:
        if proposal.delta_type == "patch":
            return merge_patch(current_payload, proposal.delta)
        if proposal.delta_type == "replace":
            return copy.deepcopy(proposal.delta)
        raise ValueError(f"Unsupported delta_type: {proposal.delta_type}")

    def _check_constraints(
        self,
        payload: Dict[str, Any],
        state_version: int,
    ) -> Optional[ValidationResult]:
        for c in self.store.constraints:
            try:
                field_value = get_path(payload, c.field)
            except KeyError:
                # Missing field does not trigger comparison constraints in v1-lite.
                continue

            violated = False
            if c.operator == "equals":
                violated = field_value == c.value
            elif c.operator == "not_equals":
                violated = field_value != c.value
            elif c.operator == "greater":
                violated = field_value > c.value
            elif c.operator == "less":
                violated = field_value < c.value
            elif c.operator == "invalid":
                violated = True
            else:
                raise ValueError(f"Unsupported constraint operator: {c.operator}")

            if violated:
                return ValidationResult(
                    valid=False,
                    reason=f"constraint_violated:{c.field}:{c.operator}",
                    discovered_constraint=DiscoveredConstraint(
                        field=c.field,
                        operator=c.operator,
                        value=c.value,
                    ),
                )
        return None

    def _decide_acceptance(
        self,
        *,
        current_score: float,
        new_score: float,
        mode: StagnationMode,
    ) -> Tuple[ProposalOutcome, str]:
        acc = self.store.run.acceptance

        if mode == "local":
            passes_threshold = new_score >= acc.threshold
            improves = new_score > current_score
            equals = acc.allow_equal and new_score == current_score
            if passes_threshold and (improves or equals):
                return "accept", "accepted_local"
            return "reject", "failed_local_acceptance"

        if mode == "exploration":
            if new_score >= acc.exploration_floor:
                return "accept", "accepted_exploration"
            return "reject", "failed_exploration_floor"

        return "reject", "engine_halted"

    def _persist_accept(
        self,
        *,
        proposal: Proposal,
        current_state: State,
        new_payload: Dict[str, Any],
        new_score: float,
        new_hash: str,
    ) -> None:
        new_state_version = current_state.state_version + 1
        new_state = State(
            run_id=self.store.run.run_id,
            state_version=new_state_version,
            payload=copy.deepcopy(new_payload),
            score=new_score,
            state_hash=new_hash,
        )
        self.store.states.append(new_state)
        self.store.accepted_hashes.add(new_hash)
        self.store.run.state_version = new_state_version

        trail_entry = TrailEntry(
            trail_id=make_id("trail"),
            proposal_id=proposal.proposal_id,
            from_state=current_state.state_version,
            to_state=new_state_version,
        )
        self.store.trail.append(trail_entry)

        best_state = self.store.best_state()
        if new_score > best_state.score:
            self.store.run.best_state_version = new_state_version

        if new_score >= self.store.run.acceptance.success_threshold:
            self.store.run.status = "converged"

    def _record_rejection(self, evaluation: Evaluation) -> None:
        if evaluation.outcome != "reject_informative":
            return
        dc = evaluation.discovered_constraint
        if dc is None:
            raise ValueError("reject_informative requires discovered_constraint")

        constraint = Constraint(
            constraint_id=make_id("constraint"),
            run_id=self.store.run.run_id,
            field=dc.field,
            operator=dc.operator,
            value=dc.value,
            state_version=self.store.current_state().state_version,
        )
        self.store.constraints.append(constraint)

    def _record_evaluation_and_counters(
        self,
        evaluation: Evaluation,
        *,
        current_score: float,
        new_score: float,
    ) -> None:
        self.store.evaluations.append(evaluation)

        # iteration increments after every evaluated proposal, including stale
        self.store.run.iteration += 1

        # no_improve_count semantics:
        # number of steps since last real score improvement
        if evaluation.outcome == "stale":
            pass
        elif evaluation.outcome == "accept" and new_score > current_score:
            self.store.run.no_improve_count = 0
        else:
            self.store.run.no_improve_count += 1

        # mode transitions
        n1 = self.store.run.stagnation.n1
        n2 = self.store.run.stagnation.n2
        count = self.store.run.no_improve_count

        if count < n1:
            self.store.run.stagnation_mode = "local"
        elif n1 <= count < n2:
            self.store.run.stagnation_mode = "exploration"
        else:
            self.store.run.stagnation_mode = "halted"
            if self.store.run.status == "active":
                self.store.run.status = "halted"

        if self.store.run.iteration >= self.store.run.max_iterations and self.store.run.status == "active":
            self.store.run.status = "halted"
            self.store.run.stagnation_mode = "halted"


# ============================================================
# Example domain: spec refinement
# ============================================================
# This is a deliberately simple example domain so you can see the
# engine run end-to-end without any LLM dependency.
# ============================================================

def validate_spec_payload(payload: Dict[str, Any]) -> ValidationResult:
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
        return ValidationResult(
            valid=False,
            reason="invalid_title",
            discovered_constraint=DiscoveredConstraint(
                field="title",
                operator="invalid",
                value=None,
            ),
        )

    if not isinstance(payload["problem"], str) or len(payload["problem"].strip()) < 20:
        return ValidationResult(
            valid=False,
            reason="problem_too_short",
            discovered_constraint=DiscoveredConstraint(
                field="problem",
                operator="invalid",
                value=None,
            ),
        )

    if not isinstance(payload["solution"], str) or len(payload["solution"].strip()) < 20:
        return ValidationResult(
            valid=False,
            reason="solution_too_short",
            discovered_constraint=DiscoveredConstraint(
                field="solution",
                operator="invalid",
                value=None,
            ),
        )

    if not isinstance(payload["budget"], (int, float)):
        return ValidationResult(
            valid=False,
            reason="budget_not_numeric",
            discovered_constraint=DiscoveredConstraint(
                field="budget",
                operator="invalid",
                value=None,
            ),
        )

    if payload["budget"] <= 0:
        return ValidationResult(
            valid=False,
            reason="budget_must_be_positive",
            discovered_constraint=DiscoveredConstraint(
                field="budget",
                operator="greater",
                value=0,
            ),
        )

    if not isinstance(payload["compliance"], bool):
        return ValidationResult(
            valid=False,
            reason="compliance_not_boolean",
            discovered_constraint=DiscoveredConstraint(
                field="compliance",
                operator="invalid",
                value=None,
            ),
        )

    if payload["compliance"] is not True:
        return ValidationResult(
            valid=False,
            reason="compliance_required",
            discovered_constraint=DiscoveredConstraint(
                field="compliance",
                operator="equals",
                value=False,
            ),
        )

    return ValidationResult(valid=True, reason="valid")


def score_spec_payload(payload: Dict[str, Any]) -> float:
    """
    Simple deterministic scalar score in [0, 1].
    Higher is better.
    """
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
    """
    Very simple deterministic proposal generator for demonstration.
    It tries to improve the weakest part of the current spec.
    No LLM involved.
    """
    state = store.current_state()
    payload = copy.deepcopy(state.payload)
    mode: ProposalMode = "explore" if store.run.stagnation_mode == "exploration" else "improve"

    if len(payload.get("problem", "").strip()) < 40:
        delta = {
            "problem": payload.get("problem", "").strip()
            + " This document explains the user pain clearly and anchors the business need."
        }
    elif len(payload.get("solution", "").strip()) < 40:
        delta = {
            "solution": payload.get("solution", "").strip()
            + " The proposed workflow is specific, practical, and measurable for delivery."
        }
    elif len(payload.get("title", "").strip()) < 8:
        delta = {"title": "Refined Product Specification"}
    elif payload.get("budget", 999999) > 10000:
        delta = {"budget": 9500}
    else:
        # In exploration we allow a lateral-ish move; otherwise nudge solution further.
        delta = {
            "solution": payload.get("solution", "").strip()
            + " It also defines acceptance criteria and implementation boundaries."
        }

    return Proposal(
        proposal_id=make_id("proposal"),
        run_id=store.run.run_id,
        based_on_state_version=state.state_version,
        mode=mode,
        delta_type="patch",
        delta=delta,
    )


def print_run_summary(store: EngineStore) -> None:
    print("\n=== RUN SUMMARY ===")
    print("Run status:", store.run.status)
    print("Iterations:", store.run.iteration)
    print("Current state version:", store.run.state_version)
    print("Best state version:", store.run.best_state_version)
    print("Stagnation mode:", store.run.stagnation_mode)
    print("No improve count:", store.run.no_improve_count)
    print("Constraints:", len(store.constraints))
    print("Accepted transitions:", len(store.trail))
    print("Current score:", store.current_state().score)
    print("Best score:", store.best_state().score)
    print("\nBest payload:")
    print(json.dumps(store.best_state().payload, indent=2, ensure_ascii=False))

    print("\nEvaluations:")
    for ev in store.evaluations:
        print(
            f"- proposal={ev.proposal_id} outcome={ev.outcome} score={ev.score} reason={ev.reason}"
        )


if __name__ == "__main__":
    initial_payload = {
        "title": "Spec",
        "problem": "Users struggle to understand what the product does.",
        "solution": "We should improve it.",
        "budget": 18000,
        "compliance": True,
    }

    engine = ConvergenceEngineV1Lite.initialize(
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
    )

    engine.run_until_stop(deterministic_demo_proposal_generator)
    print_run_summary(engine.store)
