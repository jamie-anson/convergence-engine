# Convergence Engine Schema - v1-lite (Locked)

## Purpose

A minimal, deterministic convergence loop for a single-score, single-state, single-branch system.

This version is intentionally limited. It exists to prove the engine works before adding:
- multi-evaluator logic
- branching
- rollback
- constraint expiry
- batching
- LLM evaluators
- seam composition

---

## 1. Core guarantees

This spec guarantees:
- explicit state versioning
- deterministic state transition
- deterministic evaluation order
- deterministic acceptance logic
- deterministic stagnation behaviour
- deterministic constraint extraction
- oscillation protection

Two engineers implementing this spec should produce the same runtime behaviour for the same inputs.

---

## 2. Enums

```json
{
  "proposal_outcome": [
    "accept",
    "reject_informative",
    "reject",
    "stale"
  ],
  "stagnation_mode": [
    "local",
    "exploration",
    "halted"
  ],
  "delta_type": [
    "patch",
    "replace"
  ],
  "proposal_mode": [
    "improve",
    "explore"
  ],
  "constraint_operator": [
    "equals",
    "not_equals",
    "greater",
    "less",
    "invalid"
  ]
}
```

---

## 3. EngineRun

`EngineRun` is the single source of truth for runtime behaviour.

```json
{
  "$id": "engine_run",
  "type": "object",
  "required": [
    "run_id",
    "status",
    "state_version",
    "best_state_version",
    "iteration",
    "max_iterations",
    "stagnation_mode",
    "no_improve_count",
    "acceptance",
    "stagnation"
  ],
  "properties": {
    "run_id": { "type": "string" },

    "status": {
      "type": "string",
      "enum": ["active", "converged", "halted"]
    },

    "state_version": {
      "type": "integer",
      "minimum": 0
    },

    "best_state_version": {
      "type": "integer",
      "minimum": 0
    },

    "iteration": {
      "type": "integer",
      "minimum": 0
    },

    "max_iterations": {
      "type": "integer",
      "minimum": 1
    },

    "stagnation_mode": {
      "type": "string",
      "enum": ["local", "exploration", "halted"]
    },

    "no_improve_count": {
      "type": "integer",
      "minimum": 0
    },

    "acceptance": {
      "type": "object",
      "required": [
        "threshold",
        "exploration_floor",
        "allow_equal",
        "success_threshold"
      ],
      "properties": {
        "threshold": {
          "type": "number",
          "description": "Minimum score required for acceptance in local mode."
        },
        "exploration_floor": {
          "type": "number",
          "description": "Minimum score required for acceptance in exploration mode."
        },
        "allow_equal": {
          "type": "boolean"
        },
        "success_threshold": {
          "type": "number",
          "description": "Score at or above which the run is converged."
        }
      }
    },

    "stagnation": {
      "type": "object",
      "required": ["n1", "n2"],
      "properties": {
        "n1": {
          "type": "integer",
          "minimum": 1,
          "description": "Enter exploration when no_improve_count reaches n1."
        },
        "n2": {
          "type": "integer",
          "minimum": 1,
          "description": "Halt when no_improve_count reaches n2."
        }
      }
    }
  },
  "additionalProperties": false
}
```

---

## 4. State

`State` stores the current domain payload and its scalar score.

```json
{
  "$id": "state",
  "type": "object",
  "required": [
    "run_id",
    "state_version",
    "payload",
    "score",
    "state_hash"
  ],
  "properties": {
    "run_id": { "type": "string" },

    "state_version": {
      "type": "integer",
      "minimum": 0
    },

    "payload": {
      "type": "object",
      "description": "Domain-specific structured state."
    },

    "score": {
      "type": "number",
      "description": "Normalized scalar score. Higher is always better and must be comparable across all states in the run."
    },

    "state_hash": {
      "type": "string",
      "description": "Deterministic hash of payload used for oscillation protection."
    }
  },
  "additionalProperties": false
}
```

---

## 5. Proposal

`Proposal` is the candidate change to the current state.

```json
{
  "$id": "proposal",
  "type": "object",
  "required": [
    "proposal_id",
    "run_id",
    "based_on_state_version",
    "mode",
    "delta_type",
    "delta"
  ],
  "properties": {
    "proposal_id": { "type": "string" },

    "run_id": { "type": "string" },

    "based_on_state_version": {
      "type": "integer",
      "minimum": 0
    },

    "mode": {
      "type": "string",
      "enum": ["improve", "explore"]
    },

    "delta_type": {
      "type": "string",
      "enum": ["patch", "replace"]
    },

    "delta": {
      "type": "object",
      "description": "If delta_type=patch, this must be a JSON Merge Patch (RFC 7396) against state.payload. If delta_type=replace, this must be a full replacement for state.payload."
    }
  },
  "additionalProperties": false
}
```

---

## 6. Constraint

A `Constraint` is only created from an informative rejection.

```json
{
  "$id": "constraint",
  "type": "object",
  "required": [
    "constraint_id",
    "run_id",
    "field",
    "operator",
    "value",
    "state_version"
  ],
  "properties": {
    "constraint_id": { "type": "string" },

    "run_id": { "type": "string" },

    "field": {
      "type": "string",
      "description": "Path in state.payload to which the constraint applies."
    },

    "operator": {
      "type": "string",
      "enum": ["equals", "not_equals", "greater", "less", "invalid"]
    },

    "value": {
      "description": "Must be type-compatible with field and operator. For invalid, value may be null."
    },

    "state_version": {
      "type": "integer",
      "minimum": 0
    }
  },
  "additionalProperties": false
}
```

### Constraint operator semantics

- `equals`: field must equal value to trigger the constraint
- `not_equals`: field must not equal value
- `greater`: field must be greater than value
- `less`: field must be less than value
- `invalid`: the proposed field value is domain-invalid regardless of comparison; value may be null

Type compatibility between field, operator, and value must be checked by implementation-time validation.

---

## 7. Evaluation

`Evaluation` is the system's judgement on a proposal after transition and scoring.

```json
{
  "$id": "evaluation",
  "type": "object",
  "required": [
    "evaluation_id",
    "proposal_id",
    "state_version",
    "outcome",
    "score",
    "reason",
    "discovered_constraint"
  ],
  "properties": {
    "evaluation_id": { "type": "string" },

    "proposal_id": { "type": "string" },

    "state_version": {
      "type": "integer",
      "minimum": 0,
      "description": "The state version against which the proposal was evaluated."
    },

    "outcome": {
      "type": "string",
      "enum": [
        "accept",
        "reject_informative",
        "reject",
        "stale"
      ]
    },

    "score": {
      "type": "number",
      "description": "Score of resulting state. For stale proposals, this must equal the current state's score."
    },

    "reason": {
      "type": "string"
    },

    "discovered_constraint": {
      "oneOf": [
        {
          "type": "null"
        },
        {
          "type": "object",
          "required": ["field", "operator", "value"],
          "properties": {
            "field": { "type": "string" },
            "operator": {
              "type": "string",
              "enum": ["equals", "not_equals", "greater", "less", "invalid"]
            },
            "value": {}
          },
          "additionalProperties": false
        }
      ],
      "description": "Must be populated when outcome=reject_informative. Must be null otherwise."
    }
  },
  "additionalProperties": false
}
```

---

## 8. TrailEntry

The trail records accepted transitions only.

```json
{
  "$id": "trail_entry",
  "type": "object",
  "required": [
    "trail_id",
    "proposal_id",
    "from_state",
    "to_state"
  ],
  "properties": {
    "trail_id": { "type": "string" },

    "proposal_id": { "type": "string" },

    "from_state": {
      "type": "integer",
      "minimum": 0
    },

    "to_state": {
      "type": "integer",
      "minimum": 1
    }
  },
  "additionalProperties": false
}
```

### Trail design note

`TrailEntry` is intentionally minimal.  
It is not self-describing by itself.

To reconstruct why a transition was accepted, the implementation must join:
- `trail_entry.proposal_id`
- to the corresponding `Evaluation`
- and, if needed, the `Proposal`

This is a deliberate storage simplification for v1-lite.

---

## 9. Initialisation rules

v1-lite does not generate its own initial state.

The initial state must be seeded externally.

Before the loop starts, the implementation must:
1. create `state_version = 0`
2. validate the initial payload against the domain schema
3. compute score
4. compute `state_hash`
5. set:
- `best_state_version = 0`
- `iteration = 0`
- `no_improve_count = 0`
- `stagnation_mode = local`
- `status = active`

---

## 10. Ordered execution pipeline

The engine must process each proposal in this exact order.

### Step 1 - stale check

```python
if proposal.based_on_state_version != current_state.state_version:
    outcome = stale
```

If stale:
- do not apply transition
- do not validate
- do not create constraint
- set `evaluation.score = current_state.score`
- return evaluation

### Step 2 - apply transition

```python
new_payload = transition(current_state.payload, proposal.delta, proposal.delta_type)
```

Transition rules:
- deterministic
- must not mutate the original payload
- if `delta_type = patch`, apply JSON Merge Patch (RFC 7396)
- if `delta_type = replace`, replace payload entirely

### Step 3 - schema validation

Validate `new_payload` against the domain schema.

If invalid:
- `outcome = reject_informative`
- populate `discovered_constraint`
- do not continue to scoring

### Step 4 - constraint validation

Validate `new_payload` against all active constraints.

If a constraint is violated:
- `outcome = reject_informative`
- populate `discovered_constraint`
- do not continue to scoring

### Step 5 - compute score

```python
new_score = score(new_payload)
new_state_hash = hash(new_payload)
```

Scoring must be deterministic and comparable across all states in the run.

### Step 6 - oscillation protection

Reject any proposal whose resulting `state_hash` matches a previously accepted state in the same run.

If matched:
- `outcome = reject`
- `reason = oscillation_detected`

This prevents:
- `A -> B -> A` loops
- repeated accepted-state cycling in exploration mode

### Step 7 - acceptance decision

Local mode

Accept if:

```text
new_score >= acceptance.threshold
AND (
  new_score > current_state.score
  OR (acceptance.allow_equal AND new_score == current_state.score)
)
```

Exploration mode

Accept if:

```text
new_score >= acceptance.exploration_floor
```

Exploration mode does not require improvement over current score.

### Step 8 - success check

If accepted and:

```text
new_score >= acceptance.success_threshold
```

then:
- update state
- set `status = converged`

### Step 9 - persist accepted transition

If accepted:
- increment `state_version`
- persist new `State`
- persist `TrailEntry`

### Step 10 - create constraint

If `outcome = reject_informative`:
- create `Constraint` from `evaluation.discovered_constraint`

Constraint creation must be deterministic.  
No freeform parsing step is allowed.

### Step 11 - update counters and mode

`no_improve_count` rules:
- accepted with `new_score > current_state.score` -> set to `0`
- accepted with `new_score == current_state.score` -> increment by `1`
- accepted with `new_score < current_state.score` -> increment by `1`
- reject -> increment by `1`
- reject_informative -> increment by `1`
- stale -> unchanged

This means `no_improve_count` measures:

number of steps since last real score improvement

`stagnation_mode` rules:

```python
if no_improve_count < n1:
    stagnation_mode = local

if n1 <= no_improve_count < n2:
    stagnation_mode = exploration

if no_improve_count >= n2:
    stagnation_mode = halted
    status = halted
```

`iteration` rule:

Increment `iteration` after each evaluated proposal, including stale proposals.

If `iteration >= max_iterations`:
- set `status = halted`

### Step 12 - best state tracking

If an accepted proposal produces a score strictly greater than the current best known score:
- set `best_state_version = new_state_version`

---

## 11. What v1-lite excludes

This version deliberately excludes:
- multi-evaluator systems
- Pareto logic
- branching
- rollback
- batch/tournament proposal handling
- constraint expiry or revalidation
- LLM evaluators
- observability layer
- seams
- internal reframe mechanics

---

## 12. Note on reframe

Reframe is not included in v1-lite.

Reason:  
v1-lite has no mechanism to:
- modify target definition
- modify evaluator logic
- rewrite constraint policy

So including reframe as a mode would be misleading.

It can return in a later version once those mechanics exist.

---

## 13. Final behavioural summary

v1-lite is a system where:
- an externally seeded state is refined
- proposals are applied deterministically
- invalid moves are rejected early
- informative failures produce structured constraints
- accepted-state oscillation is blocked
- stagnation moves the system from local optimisation to exploration to halt
- the best known state is always preserved

---

## 14. The bar this version should meet

If two engineers implement:
- the same domain schema
- the same transition function
- the same scoring function
- the same inputs

they should produce:
- the same accepted states
- the same trail
- the same stagnation transitions
- the same final best state

That is the test.
