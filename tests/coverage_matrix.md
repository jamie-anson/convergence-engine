# Convergence Engine v1-lite Coverage Matrix

This matrix maps the locked guarantees in [specs/convergence-engine-schema-v1-lite.md](/Users/Jammie/Code/Convergence/specs/convergence-engine-schema-v1-lite.md) to concrete tests in the suite.

## Core guarantees

- Deterministic state transition:
  `test_engine_step_semantics.py::test_patch_transition_applies_merge_patch_without_mutating_current_state`
  `test_engine_step_semantics.py::test_replace_transition_replaces_payload_entirely`
  `test_utils_and_schema.py::test_merge_patch_handles_nested_replacement_and_deletion_without_mutation`
  `test_utils_and_schema.py::test_merge_patch_replaces_target_when_patch_is_not_an_object`
- Deterministic evaluation order:
  `test_engine_step_semantics.py::test_stale_proposal_is_rejected_without_state_or_constraint_mutation`
  `test_engine_step_semantics.py::test_schema_invalid_proposal_creates_constraint`
  `test_engine_step_semantics.py::test_active_constraint_violation_creates_informative_rejection`
  `test_engine_step_semantics.py::test_oscillation_rejects_previously_accepted_state`
- Informative rejection to constraint extraction:
  `test_engine_constraints.py::test_reject_informative_creates_exactly_one_constraint_with_expected_fields`
  `test_engine_constraints.py::test_non_informative_rejections_do_not_create_constraints`
- Oscillation protection:
  `test_engine_step_semantics.py::test_oscillation_rejects_previously_accepted_state`
- Local and exploration acceptance logic:
  `test_engine_step_semantics.py::test_local_acceptance_requires_threshold_and_improvement`
  `test_engine_step_semantics.py::test_exploration_mode_accepts_when_floor_is_met`
  `test_engine_step_semantics.py::test_exploration_mode_rejects_when_floor_is_not_met`
  `test_engine_counters_and_modes.py::test_allow_equal_accepts_equal_score_but_does_not_advance_best_state`
- Stagnation counter semantics:
  `test_engine_counters_and_modes.py::test_iteration_increments_for_every_evaluated_proposal_including_stale`
  `test_engine_counters_and_modes.py::test_no_improve_count_is_unchanged_for_stale`
  `test_engine_counters_and_modes.py::test_no_improve_count_resets_only_on_strict_improvement`
  `test_engine_counters_and_modes.py::test_no_improve_count_increments_on_reject_and_informative_reject`
- Mode transitions:
  `test_engine_counters_and_modes.py::test_mode_transitions_happen_exactly_at_n1_and_n2`
  `test_engine_counters_and_modes.py::test_halting_by_stagnation_sets_status_and_mode`
- Iteration and max-iteration halting:
  `test_engine_step_semantics.py::test_max_iterations_halts_even_without_stagnation_threshold`
  `test_engine_counters_and_modes.py::test_halting_by_max_iterations_sets_status_and_mode`
- Best-state tracking:
  `test_engine_counters_and_modes.py::test_allow_equal_accepts_equal_score_but_does_not_advance_best_state`
  `test_engine_records_and_determinism.py::test_current_state_and_best_state_track_run_correctly`

## Schema and persistence shape

- Seed initialization rules:
  `test_engine_initialization.py::test_initialize_creates_expected_seeded_run_state`
  `test_engine_initialization.py::test_initialize_populates_initial_score_hash_and_best_state_deterministically`
- Constraint operator semantics:
  `test_engine_constraints.py::test_equals_constraint_is_enforced`
  `test_engine_constraints.py::test_not_equals_constraint_is_enforced`
  `test_engine_constraints.py::test_greater_constraint_is_enforced`
  `test_engine_constraints.py::test_less_constraint_is_enforced`
  `test_engine_constraints.py::test_invalid_constraint_is_enforced`
  `test_engine_constraints.py::test_missing_constraint_path_is_ignored`
- Runtime object schema shape:
  `test_utils_and_schema.py::test_machine_readable_schema_files_are_valid_json_objects`
  `test_utils_and_schema.py::test_runtime_objects_match_checked_in_schema_shapes`

## Determinism and regression coverage

- Byte-stable run serialization:
  `test_engine_records_and_determinism.py::test_identical_runs_serialize_to_identical_canonical_json`
- Deterministic runtime identifiers:
  `test_engine_records_and_determinism.py::test_generated_ids_are_deterministic_within_a_run`
- Example integrations as regression coverage:
  `test_engine_records_and_determinism.py::test_spec_refinement_example_reaches_expected_best_state`
  `test_engine_records_and_determinism.py::test_meeting_example_reaches_conflict_free_selection`
