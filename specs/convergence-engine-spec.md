# Convergence Engine - Specification (v3)

Deterministic state convergence with explicit evaluation, constraint shaping, and controlled search

---

## 1. Intent

The Convergence Engine exists to:

Resolve problems by searching over structured state using explicit evaluators and constraints, without reliance on conversational memory.

It replaces:
- context accumulation
- implicit reasoning
- unbounded agent debate

With:
- defined state
- explicit evaluation
- constrained search
- controlled exploration

---

## 2. Core Principle

The system retains only what changes future search.

Specifically:
- current state
- accepted transitions
- active constraints

All other information is discarded.

---

## 3. System Model

The engine operates as a state-transition system with evaluation.

At each step:
1. A proposal modifies the state
2. Evaluators score the result
3. The system accepts, rejects, or branches
4. State and constraints update accordingly

---

## 4. Core Primitives

### 4.1 Target

Defines success.

Must include:
- success condition (boolean or threshold)
- evaluation dimensions

### 4.2 State

A structured, versioned representation of the problem.

Properties:
- explicit (no hidden variables)
- minimal (only required fields)
- overwriteable
- versioned

```json
{
  "state_version": 12,
  "data": {}
}
```

### 4.3 Evaluators

Evaluators define progress.

They are mandatory and first-class.

#### Evaluator Contract

```json
{
  "name": "string",
  "type": "deterministic | rule_based | llm",
  "criteria": ["..."],
  "output": {
    "score": "float | vector",
    "pass": "boolean",
    "reason_code": "enum"
  }
}
```

#### Evaluator Execution Model

Tiered Evaluation (mandatory):
1. Fast Path
- deterministic / rule checks
- reject immediately if failed
2. Slow Path
- LLM or complex evaluation
- only executed if fast path passes

#### Multi-Evaluator Composition

The system must define:
- acceptance rule
- priority order
- relaxation policy

### 4.4 Acceptance Function

Formal rule over evaluator outputs.

Must be explicit and deterministic.

Examples:

```text
accept if:
  product >= 0.8
  AND engineering >= 0.7
  AND cost <= 10
```

### 4.5 Constraint Field

Stores constraints that affect future search.

Each constraint must include:

```json
{
  "constraint": "...",
  "scope": "...",
  "origin_state_version": 10,
  "expiry": "condition",
  "confidence": 1.0
}
```

#### Constraint Rules

- Only store constraints that reduce search space
- Constraints must be revalidated if state changes beyond origin scope
- Expired constraints must be removed

### 4.6 Trail

Records accepted transitions.

```json
{
  "from_state": 11,
  "to_state": 12,
  "delta": {},
  "evaluator_result": {}
}
```

### 4.7 State Distiller (Deterministic Core)

The Distiller is not an LLM by default.

It is a deterministic transformation:

```json
{
  "current_state": {},
  "active_constraints": [],
  "evaluator_criteria": [],
  "recent_deltas": []
}
```

#### Distiller Rules

- no narrative summarisation
- no interpretation
- no loss of critical constraints
- schema-defined outputs only

#### Optional LLM Layer (Non-authoritative)

May:
- suggest proposal directions
- highlight patterns

May NOT:
- modify state
- define truth
- override evaluators

### 4.8 Proposal Strategy

Agents must generate proposals using:
1. constraint awareness
2. evaluator awareness
3. local search (small deltas)
4. optional exploratory moves

Agents MUST receive:
- evaluator criteria
- current constraints

### 4.9 Stagnation Protocol

Triggered when:
- no improvement after N iterations
- score plateau
- oscillation detected

#### Mode Transition Ladder (mandatory)

Mode 1: Local Optimisation  
-> after N1 failures -> Mode 2

Mode 2: Exploration  
-> allow lateral / degrading moves  
-> after N2 failures -> Mode 3

Mode 3: Reframe  
-> adjust target / constraints  
-> after N3 failures -> Mode 4

Mode 4: Escalation  
-> halt + request external input

#### Oscillation Detection

If:
- state A -> B -> A

Then:
-> force transition to Reframe

### 4.10 Branching & Rollback

The system must support:

Checkpoints

```json
{
  "checkpoint_id": "...",
  "state": {}
}
```

Rules:
- branches originate from checkpoints
- failed branches revert to last checkpoint
- state overwrite applies only within branch

### 4.11 Concurrency Control

Each proposal must include:

```json
{
  "based_on_state_version": 12
}
```

Rules:
- proposals based on stale state are rejected
- evaluation always occurs on latest state

---

## 5. Proposal Lifecycle

Each proposal is classified:

### A. Accept - Improving

- improves evaluator score
- or satisfies target

Action:
- update state
- append to trail

### B. Reject - Informative

- fails but reveals constraint

Action:
- update constraint field

### C. Reject - Non-informative

- fails without insight

Action:
- discard

### D. Branch - Exploratory

- allowed under stagnation protocol

Action:
- create new branch

---

## 6. Multi-Evaluator Conflict Handling

### 6.1 Pareto Mode

Maintain non-dominated states when objectives conflict.

### 6.2 Constraint Relaxation

When no feasible solution exists:
- relax lowest priority evaluator first
- reattempt convergence

### 6.3 Constraint Failure Detection

If all proposals fail:

-> surface constraint conflict as root cause

---

## 7. Convergence Conditions

### 7.1 Success

- all evaluator conditions satisfied

### 7.2 Converged Without Success

- no valid moves remain
- constraints block all paths

### 7.3 Resource Bound

- iteration / cost / time limit reached

---

## 8. Proposal Engine (Agent Model)

Agents are:

constraint-aware, evaluator-aware proposal generators

They:
- operate on distilled state
- do not access raw history
- optimise proposals toward evaluator criteria

---

## 9. Seams (Structural Composition)

A Seam is a bounded convergence unit.

Each seam defines:
- target
- evaluators
- constraints
- acceptance function

### System Composition

```text
Seam A -> converges -> output state
|
v
Seam B -> consumes output
|
v
Seam C -> ...
```

Rule:

Output of one seam becomes input constraint of the next.

---

## 10. Failure Modes

### 10.1 Looping

Mitigation: constraint field

### 10.2 Evaluator Drift

Mitigation: strict schemas + fast path checks

### 10.3 State Corruption

Mitigation: versioning + concurrency control

### 10.4 False Constraints

Mitigation: constraint expiry + revalidation

### 10.5 Premature Convergence

Mitigation: stagnation protocol

### 10.6 Silent Degradation (Distiller Risk)

Mitigation:
- deterministic distiller
- schema enforcement
- no narrative compression

---

## 11. Example - Meeting Scheduler

Target:  
0 conflicts

State:

```json
{
  "state_version": 3,
  "conflicts": 1,
  "candidates": []
}
```

Constraint Field:
- Monday 9am invalid

Trail:
- remove Monday -> conflicts = 2
- try Tuesday 2pm -> conflicts = 1
- try Tuesday 3pm -> conflicts = 0

Convergence:
-> Tuesday 3pm selected

---

## 12. Key Insight

Intelligence is the elimination of invalid paths under explicit evaluation.

---

## 13. Summary

The Convergence Engine is:

A deterministic, evaluator-driven search system over structured state, with constraint shaping and controlled exploration.

It does not rely on:
- memory
- conversation
- implicit reasoning

It relies on:
- state
- evaluators
- constraints
- disciplined search

---

# Convergence Engine - v3.1 Addendum

## 1. Initialisation Phase

The engine does not begin from an empty state.

Before the convergence loop starts, the system must create a valid seeded state.

Rule:

A Convergence run must begin with:
- target
- schema
- evaluator contracts
- initial populated state

Initialisation sources:
- human input
- deterministic import
- agent-generated baseline
- prior seam output

Constraint:

The main convergence loop may only begin once the state passes schema validation.

Why this matters:

The engine is designed for iterative convergence, not creation from nothing.

So the principle becomes:

Generation seeds the search. Convergence refines it.

That's especially important for specs, plans, copy structures, and other generative domains.

---

## 2. Proposal Batching / Tournament Mode

Parallel agents should not race first-come-first-served against the same state version.

Rule:

When multiple agents generate proposals from the same `state_version`, the engine may enter batch evaluation mode.

Batch flow:
1. Collect proposals generated from the same state version
2. Evaluate all proposals against that same state version
3. Rank proposals by acceptance function
4. Accept the best valid proposal
5. Reject the remainder
6. Advance state version once

Benefit:

This turns concurrency from waste into search coverage.

Note:

If batching is disabled, stale proposals are rejected by version mismatch as defined in v3.

---

## 3. Constraint Challenging

Low-confidence constraints must not quietly become dogma.

Rule:

During stagnation exploration, the engine must be allowed to challenge constraints below a configured confidence threshold or within an eligible expiry scope.

Mechanism:

In Mode 2: Exploration, the engine may intentionally test proposals that violate:
- low-confidence constraints
- stale constraints
- low-priority constraints

Outcome:

If the proposal succeeds:
- the constraint is weakened or removed

If it fails:
- the constraint confidence increases

Why this matters:

This prevents epistemic closure.

The system must be able to discover not only:
- what is impossible

but also:
- which previous impossibilities were wrong

---

## 4. Global Invariants

Evaluator optimisation must not bypass common sense.

Rule:

Every run must declare a set of global invariants enforced in the fast path.

These are non-negotiable constraints that proposals cannot trade away.

Examples:

For meeting scheduling:
- duration must be at least 15 minutes
- meeting must occur within allowed hours
- all required attendees must be included

For spec refinement:
- must not remove mandatory compliance requirements
- must preserve schema validity
- must not exceed hard budget ceiling

Principle:

Evaluators optimise within bounds.  
Global invariants define the bounds.

This protects the engine from Goodhart-style gaming.

---

## 5. Branch Merge Policy

Branches need an explicit outcome policy.

Default rule:

Branches do not merge automatically.

The engine selects:
- best successful branch
- or best Pareto-valid branch
- or escalates to human choice

Optional merge mode:

A merge is only allowed if:
- state schema supports composability
- deltas touch non-conflicting fields
- merge passes all evaluators and invariants

Principle:

No implicit synthesis.

That keeps branch behaviour legible and safe.

---

## 6. Proposal Diversity Policy

Multiple agents should explore meaningfully different areas of the search space.

Rule:

In multi-agent mode, proposal generators should be assigned differentiated search roles.

Examples:

Agents may vary by:
- evaluator priority emphasis
- delta size
- constraint subset focus
- risk tolerance
- exploration vs optimisation bias

Principle:

Multi-agent systems should create search diversity, not duplicated guesses.

---

## 7. Observability Contract

The engine should expose its convergence behaviour operationally.

Minimum runtime metrics:

Every implementation should expose:
- current state version
- current stagnation mode
- evaluator score trajectory
- acceptance rate
- rejection rate by type
- constraint field count and growth rate
- branch count
- stale proposal rate
- rollback count
- relaxation events
- constraint challenge events

Purpose:

Observability is not part of search logic, but it is required for:
- debugging
- tuning
- comparing deployments
- diagnosing false stagnation or evaluator problems
