from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Literal, Optional

ProposalOutcome = Literal["accept", "reject_informative", "reject", "stale"]
StagnationMode = Literal["local", "exploration", "halted"]
DeltaType = Literal["patch", "replace"]
ProposalMode = Literal["improve", "explore"]
ConstraintOperator = Literal["equals", "not_equals", "greater", "less", "invalid"]


@dataclass(slots=True)
class AcceptanceConfig:
    threshold: float
    exploration_floor: float
    allow_equal: bool
    success_threshold: float


@dataclass(slots=True)
class StagnationConfig:
    n1: int
    n2: int


@dataclass(slots=True)
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


@dataclass(slots=True)
class State:
    run_id: str
    state_version: int
    payload: Dict[str, Any]
    score: float
    state_hash: str


@dataclass(slots=True)
class Proposal:
    proposal_id: str
    run_id: str
    based_on_state_version: int
    mode: ProposalMode
    delta_type: DeltaType
    delta: Dict[str, Any]


@dataclass(slots=True)
class DiscoveredConstraint:
    field: str
    operator: ConstraintOperator
    value: Any


@dataclass(slots=True)
class Constraint:
    constraint_id: str
    run_id: str
    field: str
    operator: ConstraintOperator
    value: Any
    state_version: int


@dataclass(slots=True)
class Evaluation:
    evaluation_id: str
    proposal_id: str
    state_version: int
    outcome: ProposalOutcome
    score: float
    reason: str
    discovered_constraint: Optional[DiscoveredConstraint]


@dataclass(slots=True)
class TrailEntry:
    trail_id: str
    proposal_id: str
    from_state: int
    to_state: int


@dataclass(slots=True)
class ValidationResult:
    valid: bool
    reason: str
    discovered_constraint: Optional[DiscoveredConstraint] = None

