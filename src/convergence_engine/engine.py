from __future__ import annotations

import copy
from typing import Any, Callable, Optional, Tuple

from .storage import EngineStore, InMemoryEngineStore
from .types import (
    AcceptanceConfig,
    Constraint,
    DiscoveredConstraint,
    EngineRun,
    Evaluation,
    Proposal,
    ProposalOutcome,
    StagnationConfig,
    StagnationMode,
    State,
    TrailEntry,
    ValidationResult,
)
from .utils import get_path, make_id, merge_patch, payload_hash

ValidatorFn = Callable[[dict[str, Any]], ValidationResult]
ScoreFn = Callable[[dict[str, Any]], float]
ProposalGeneratorFn = Callable[[EngineStore], Proposal]


class ConvergenceEngineV1Lite:
    """Deterministic single-score, single-state, single-branch convergence engine."""

    def __init__(self, store: EngineStore, validator: ValidatorFn, scorer: ScoreFn):
        self.store = store
        self.validator = validator
        self.scorer = scorer
        self._id_counters: dict[str, int] = {}

    @classmethod
    def initialize(
        cls,
        initial_payload: dict[str, Any],
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

        store = InMemoryEngineStore(
            run=run,
            states=[initial_state],
            accepted_hashes={initial_state.state_hash},
        )
        return cls(store=store, validator=validator, scorer=scorer)

    def step(self, proposal: Proposal) -> Evaluation:
        if self.store.run.status != "active":
            raise RuntimeError(f"Engine is not active: {self.store.run.status}")

        current_state = self.store.current_state()
        self.store.proposals.append(proposal)

        if proposal.based_on_state_version != current_state.state_version:
            evaluation = Evaluation(
                evaluation_id=self._next_id("eval"),
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

        new_payload = self._transition(current_state.payload, proposal)

        schema_validation = self.validator(copy.deepcopy(new_payload))
        if not schema_validation.valid:
            evaluation = Evaluation(
                evaluation_id=self._next_id("eval"),
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

        constraint_failure = self._check_constraints(new_payload)
        if constraint_failure is not None:
            evaluation = Evaluation(
                evaluation_id=self._next_id("eval"),
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

        new_score = self.scorer(copy.deepcopy(new_payload))
        new_hash = payload_hash(new_payload)

        if new_hash in self.store.accepted_hashes:
            evaluation = Evaluation(
                evaluation_id=self._next_id("eval"),
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

        outcome, reason = self._decide_acceptance(
            current_score=current_state.score,
            new_score=new_score,
            mode=self.store.run.stagnation_mode,
        )

        evaluation = Evaluation(
            evaluation_id=self._next_id("eval"),
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

    def _transition(self, current_payload: dict[str, Any], proposal: Proposal) -> dict[str, Any]:
        if proposal.delta_type == "patch":
            return merge_patch(current_payload, proposal.delta)
        if proposal.delta_type == "replace":
            return copy.deepcopy(proposal.delta)
        raise ValueError(f"Unsupported delta_type: {proposal.delta_type}")

    def _check_constraints(self, payload: dict[str, Any]) -> Optional[ValidationResult]:
        for constraint in self.store.constraints:
            try:
                field_value = get_path(payload, constraint.field)
            except KeyError:
                continue

            if constraint.operator == "equals":
                violated = field_value == constraint.value
            elif constraint.operator == "not_equals":
                violated = field_value != constraint.value
            elif constraint.operator == "greater":
                violated = field_value > constraint.value
            elif constraint.operator == "less":
                violated = field_value < constraint.value
            elif constraint.operator == "invalid":
                violated = True
            else:
                raise ValueError(f"Unsupported constraint operator: {constraint.operator}")

            if violated:
                return ValidationResult(
                    valid=False,
                    reason=f"constraint_violated:{constraint.field}:{constraint.operator}",
                    discovered_constraint=DiscoveredConstraint(
                        field=constraint.field,
                        operator=constraint.operator,
                        value=constraint.value,
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
        acceptance = self.store.run.acceptance

        if mode == "local":
            passes_threshold = new_score >= acceptance.threshold
            improves = new_score > current_score
            equals = acceptance.allow_equal and new_score == current_score
            if passes_threshold and (improves or equals):
                return "accept", "accepted_local"
            return "reject", "failed_local_acceptance"

        if mode == "exploration":
            if new_score >= acceptance.exploration_floor:
                return "accept", "accepted_exploration"
            return "reject", "failed_exploration_floor"

        return "reject", "engine_halted"

    def _next_id(self, prefix: str) -> str:
        current = self._id_counters.get(prefix, 0)
        self._id_counters[prefix] = current + 1
        return f"{prefix}_{current:04d}"

    def _persist_accept(
        self,
        *,
        proposal: Proposal,
        current_state: State,
        new_payload: dict[str, Any],
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

        self.store.trail.append(
            TrailEntry(
                trail_id=self._next_id("trail"),
                proposal_id=proposal.proposal_id,
                from_state=current_state.state_version,
                to_state=new_state_version,
            )
        )

        if new_score > self.store.best_state().score:
            self.store.run.best_state_version = new_state_version

        if new_score >= self.store.run.acceptance.success_threshold:
            self.store.run.status = "converged"

    def _record_rejection(self, evaluation: Evaluation) -> None:
        if evaluation.outcome != "reject_informative":
            return
        discovered = evaluation.discovered_constraint
        if discovered is None:
            raise ValueError("reject_informative requires discovered_constraint")

        self.store.constraints.append(
            Constraint(
                constraint_id=self._next_id("constraint"),
                run_id=self.store.run.run_id,
                field=discovered.field,
                operator=discovered.operator,
                value=discovered.value,
                state_version=self.store.current_state().state_version,
            )
        )

    def _record_evaluation_and_counters(
        self,
        evaluation: Evaluation,
        *,
        current_score: float,
        new_score: float,
    ) -> None:
        self.store.evaluations.append(evaluation)
        self.store.run.iteration += 1

        if evaluation.outcome == "stale":
            pass
        elif evaluation.outcome == "accept" and new_score > current_score:
            self.store.run.no_improve_count = 0
        else:
            self.store.run.no_improve_count += 1

        n1 = self.store.run.stagnation.n1
        n2 = self.store.run.stagnation.n2
        no_improve_count = self.store.run.no_improve_count

        if no_improve_count < n1:
            self.store.run.stagnation_mode = "local"
        elif n1 <= no_improve_count < n2:
            self.store.run.stagnation_mode = "exploration"
        else:
            self.store.run.stagnation_mode = "halted"
            if self.store.run.status == "active":
                self.store.run.status = "halted"

        if self.store.run.iteration >= self.store.run.max_iterations and self.store.run.status == "active":
            self.store.run.status = "halted"
            self.store.run.stagnation_mode = "halted"
