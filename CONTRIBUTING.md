# Contributing

## Principles

Convergence Engine optimizes for correctness, determinism, and spec fidelity before feature breadth. Contributions should preserve the locked `v1-lite` semantics unless the change explicitly updates the written spec.

## Local setup

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Expectations for changes

- Keep engine behavior deterministic for identical inputs.
- Update tests whenever behavior changes.
- Keep examples outside the core engine package.
- Do not add branching, rollback, multi-evaluator logic, batching, seam composition, or LLM evaluators to `v1-lite`.
- If a schema-shaped runtime object changes, update both:
  - package schemas under `src/convergence_engine/schemas/v1-lite`
  - published schemas under `schemas/v1-lite`

## Pull requests

- Explain which part of the written spec the change implements or protects.
- Include tests for regressions and edge cases.
- Note any compatibility implications for embedders.

