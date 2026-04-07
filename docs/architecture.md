# Convergence Engine Architecture Boundary

## Current scope: v1-lite

The current implementation is the minimum trustworthy convergence core:

- one active state at a time
- one scalar score
- one accepted path
- deterministic validation, scoring, acceptance, and stagnation
- in-memory runtime storage

The package is intended to be embedded inside a larger host system. The host owns domain modeling, validation, scoring, and proposal generation. The engine owns deterministic progression through the convergence loop.

## Core subsystems

### Engine

Owns the ordered proposal lifecycle defined in the locked schema:
- stale check
- transition
- schema validation
- constraint validation
- score and hash computation
- oscillation protection
- acceptance decision
- accepted transition persistence
- counter and stagnation updates

### Types and schemas

Runtime objects are represented as typed Python dataclasses and mirrored as JSON Schemas so external systems can validate inputs and outputs without importing Python internals.

The package also includes lightweight runtime schema validation and serialization helpers so host systems can:
- assert object shape at integration boundaries
- export full run artifacts to JSON for persistence or debugging
- consume the same schema definitions inside and outside Python

### Storage

`v1-lite` uses an in-memory store. Storage is separated from engine behavior so later versions can add durable backends without changing convergence semantics.

### Examples

Examples are intentionally outside the core engine. They demonstrate embedding patterns:
- spec refinement for simple deterministic text-structure improvement
- meeting orchestration for seeded scheduling state and host-driven proposal generation

## Roadmap boundary

The following are intentionally deferred until after `v1-lite` is stable:

- multi-evaluator and Pareto search
- branching and rollback
- batch proposal evaluation
- constraint expiry and revalidation
- LLM-assisted evaluators
- seam composition
- observability and runtime metrics

The current repository should optimize for correctness, clarity, and spec fidelity over feature expansion.
