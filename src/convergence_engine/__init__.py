"""Public package API for Convergence Engine v1-lite."""

from .engine import ConvergenceEngineV1Lite
from .serialization import serialize_engine, serialize_store, to_json, to_plain_data
from .storage import EngineStore, InMemoryEngineStore
from .types import (
    AcceptanceConfig,
    Constraint,
    ConstraintOperator,
    DeltaType,
    DiscoveredConstraint,
    EngineRun,
    Evaluation,
    Proposal,
    ProposalMode,
    ProposalOutcome,
    StagnationConfig,
    StagnationMode,
    State,
    TrailEntry,
    ValidationResult,
)
from .validation import SchemaValidationError, assert_valid_named_schema, load_schema, validate_named_schema

__all__ = [
    "AcceptanceConfig",
    "Constraint",
    "ConstraintOperator",
    "ConvergenceEngineV1Lite",
    "DeltaType",
    "DiscoveredConstraint",
    "EngineRun",
    "EngineStore",
    "Evaluation",
    "InMemoryEngineStore",
    "Proposal",
    "ProposalMode",
    "ProposalOutcome",
    "SchemaValidationError",
    "StagnationConfig",
    "StagnationMode",
    "State",
    "TrailEntry",
    "ValidationResult",
    "assert_valid_named_schema",
    "load_schema",
    "serialize_engine",
    "serialize_store",
    "to_json",
    "to_plain_data",
    "validate_named_schema",
]
