# Convergence Engine

Convergence Engine is a deterministic search core for structured state. It is designed for systems that need explicit evaluation, explicit constraints, and reproducible behavior rather than conversational memory or unbounded agent debate.

This repository currently focuses on `v1-lite`: a Python-first, single-score, single-state, single-branch engine that proves the core convergence loop works before adding multi-evaluator logic, branching, rollback, batching, seam composition, or LLM evaluators.

## What v1-lite includes

- Seeded-state initialization
- Deterministic proposal transition with JSON Merge Patch support
- Deterministic validation and scoring hooks
- Informative rejection to structured constraint creation
- Accepted-state oscillation protection via state hashing
- Deterministic stagnation transitions: `local -> exploration -> halted`
- In-memory runtime storage with a clean embedding surface
- Machine-readable JSON Schemas for runtime objects
- Built-in schema loading, runtime shape validation, and JSON serialization helpers
- Example domains for spec refinement and meeting orchestration

## What v1-lite excludes

- Multi-evaluator or Pareto search
- Branching and rollback
- Batch/tournament proposal handling
- Constraint expiry or revalidation
- LLM evaluators
- Seam composition
- Observability layer
- CLI or UI surface

## When to use it

Use Convergence Engine when your system can:
- represent the problem as structured state
- define deterministic validation and scoring
- generate proposals against the latest known state
- benefit from reproducible search behavior

It is a good fit for orchestration systems like an Agentic Meeting Orchestrator, where a host system wants explicit state progression and deterministic outcomes.

## When not to use it

Avoid `v1-lite` when you need:
- free-form brainstorming without a structured state model
- non-deterministic scoring as the primary evaluator
- branch merging or rollback
- optimization across conflicting objectives

## Public embedding model

The intended extension points are:

- `validator(payload) -> ValidationResult`
- `scorer(payload) -> float`
- `proposal_generator(store) -> Proposal`

Embedding guarantees and requirements:

- validators and scorers must be deterministic
- scores must be comparable across all states in a run
- proposal generators must set `based_on_state_version`
- initial payloads must already satisfy the domain schema

## Runtime utilities

The package also exposes production-facing helpers for embedders:

- `load_schema(name)` to load the packaged `v1-lite` JSON Schemas
- `validate_named_schema(value, name)` to validate runtime objects against a named schema
- `assert_valid_named_schema(value, name)` to fail fast on invalid runtime shapes
- `serialize_engine(engine)` and `serialize_store(store)` to export run artifacts as plain JSON-compatible dictionaries
- `to_json(value)` to emit stable JSON for logs, snapshots, or persisted artifacts

## Package layout

- `src/convergence_engine`: core library
- `schemas/v1-lite`: machine-readable JSON Schemas
- `examples/spec_refinement.py`: simple deterministic example
- `examples/meeting_orchestrator.py`: meeting-oriented reference integration
- `docs/architecture.md`: roadmap boundaries
- `specs/convergence-engine-schema-v1-lite.md`: locked written schema

## Quick start

```python
from convergence_engine import ConvergenceEngineV1Lite

engine = ConvergenceEngineV1Lite.initialize(
    initial_payload=seeded_payload,
    validator=validator,
    scorer=scorer,
    threshold=0.55,
    exploration_floor=0.40,
    allow_equal=False,
    success_threshold=0.90,
    n1=3,
    n2=6,
    max_iterations=12,
)

engine.run_until_stop(proposal_generator)
best_state = engine.store.best_state()
```

## Development

Run the test suite with:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

CI is defined in `.github/workflows/ci.yml` and runs the full suite on push and pull request.

The initial release is tracked in `v0.1.0`.
