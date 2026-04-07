from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Protocol, Set

from .types import Constraint, EngineRun, Evaluation, Proposal, State, TrailEntry


class EngineStore(Protocol):
    run: EngineRun
    states: List[State]
    proposals: List[Proposal]
    evaluations: List[Evaluation]
    constraints: List[Constraint]
    trail: List[TrailEntry]
    accepted_hashes: Set[str]

    def current_state(self) -> State:
        ...

    def best_state(self) -> State:
        ...


@dataclass
class InMemoryEngineStore:
    run: EngineRun
    states: List[State] = field(default_factory=list)
    proposals: List[Proposal] = field(default_factory=list)
    evaluations: List[Evaluation] = field(default_factory=list)
    constraints: List[Constraint] = field(default_factory=list)
    trail: List[TrailEntry] = field(default_factory=list)
    accepted_hashes: Set[str] = field(default_factory=set)

    def current_state(self) -> State:
        return self.states[-1]

    def best_state(self) -> State:
        return self.states[self.run.best_state_version]

