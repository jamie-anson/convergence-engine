from __future__ import annotations

import unittest

from convergence_engine import Constraint
from tests.helpers import accepted_improvement_proposal, build_engine, deepcopy_payload, make_proposal


class EngineStepSemanticsTests(unittest.TestCase):
    def test_stale_proposal_is_rejected_without_state_or_constraint_mutation(self):
        engine = build_engine()
        proposal = make_proposal(
            engine,
            proposal_id="proposal_stale",
            based_on_state_version=99,
            delta={"title": "Ignored"},
        )

        evaluation = engine.step(proposal)

        self.assertEqual("stale", evaluation.outcome)
        self.assertEqual("stale_proposal", evaluation.reason)
        self.assertEqual(0, engine.store.run.state_version)
        self.assertEqual(0, len(engine.store.constraints))
        self.assertEqual(engine.store.current_state().score, evaluation.score)

    def test_patch_transition_applies_merge_patch_without_mutating_current_state(self):
        engine = build_engine()
        original_payload = deepcopy_payload(engine.store.current_state().payload)
        proposal = make_proposal(
            engine,
            proposal_id="proposal_patch",
            delta={"title": "Refined Product Specification"},
        )

        evaluation = engine.step(proposal)

        self.assertEqual("accept", evaluation.outcome)
        self.assertEqual(original_payload["title"], "Spec")
        self.assertEqual("Refined Product Specification", engine.store.current_state().payload["title"])

    def test_replace_transition_replaces_payload_entirely(self):
        engine = build_engine()
        replacement = {
            "title": "Replacement Spec",
            "problem": "Users struggle to understand what the product does with enough detail to validate.",
            "solution": "A rewritten solution paragraph that is long enough to satisfy validation rules.",
            "budget": 5000,
            "compliance": True,
        }
        proposal = make_proposal(
            engine,
            proposal_id="proposal_replace",
            delta=replacement,
            delta_type="replace",
        )

        evaluation = engine.step(proposal)

        self.assertEqual("accept", evaluation.outcome)
        self.assertEqual(replacement, engine.store.current_state().payload)

    def test_schema_invalid_proposal_creates_constraint(self):
        engine = build_engine()
        proposal = make_proposal(
            engine,
            proposal_id="proposal_invalid",
            delta={"title": ""},
        )

        evaluation = engine.step(proposal)

        self.assertEqual("reject_informative", evaluation.outcome)
        self.assertEqual("invalid_title", evaluation.reason)
        self.assertEqual(1, len(engine.store.constraints))

    def test_active_constraint_violation_creates_informative_rejection(self):
        engine = build_engine()
        engine.store.constraints.append(
            Constraint(
                constraint_id="constraint_budget",
                run_id=engine.store.run.run_id,
                field="budget",
                operator="greater",
                value=10000,
                state_version=0,
            )
        )
        proposal = make_proposal(
            engine,
            proposal_id="proposal_constraint",
            delta={
                "budget": 12000,
                "solution": "This is now long enough to pass the length requirement cleanly.",
            },
        )

        evaluation = engine.step(proposal)

        self.assertEqual("reject_informative", evaluation.outcome)
        self.assertTrue(evaluation.reason.startswith("constraint_violated:budget"))

    def test_oscillation_rejects_previously_accepted_state(self):
        engine = build_engine()
        accepted = engine.step(accepted_improvement_proposal(engine, proposal_id="proposal_up"))
        self.assertEqual("accept", accepted.outcome)

        revert = make_proposal(
            engine,
            proposal_id="proposal_revert",
            based_on_state_version=1,
            delta=deepcopy_payload(engine.store.states[0].payload),
            delta_type="replace",
        )

        evaluation = engine.step(revert)

        self.assertEqual("reject", evaluation.outcome)
        self.assertEqual("oscillation_detected", evaluation.reason)

    def test_local_acceptance_requires_threshold_and_improvement(self):
        engine = build_engine()
        proposal = make_proposal(
            engine,
            proposal_id="proposal_weak",
            delta={"title": "Better"},
        )

        evaluation = engine.step(proposal)

        self.assertEqual("reject", evaluation.outcome)
        self.assertEqual("failed_local_acceptance", evaluation.reason)

    def test_exploration_mode_accepts_when_floor_is_met(self):
        engine = build_engine()
        engine.store.run.no_improve_count = 3
        engine.store.run.stagnation_mode = "exploration"
        proposal = make_proposal(
            engine,
            proposal_id="proposal_explore_accept",
            mode="explore",
            delta={"budget": 15000},
        )

        evaluation = engine.step(proposal)

        self.assertEqual("accept", evaluation.outcome)
        self.assertEqual("accepted_exploration", evaluation.reason)

    def test_exploration_mode_rejects_when_floor_is_not_met(self):
        engine = build_engine(exploration_floor=0.60)
        engine.store.run.no_improve_count = 3
        engine.store.run.stagnation_mode = "exploration"
        proposal = make_proposal(
            engine,
            proposal_id="proposal_explore_reject",
            mode="explore",
            delta={"budget": 50000},
        )

        evaluation = engine.step(proposal)

        self.assertEqual("reject", evaluation.outcome)
        self.assertEqual("failed_exploration_floor", evaluation.reason)

    def test_max_iterations_halts_even_without_stagnation_threshold(self):
        engine = build_engine(n1=10, n2=11, max_iterations=2)
        engine.step(make_proposal(engine, proposal_id="proposal_first", delta={"title": ""}))
        evaluation = engine.step(make_proposal(engine, proposal_id="proposal_second", delta={"title": ""}))

        self.assertEqual("reject_informative", evaluation.outcome)
        self.assertEqual(2, engine.store.run.iteration)
        self.assertEqual("halted", engine.store.run.status)
        self.assertEqual("halted", engine.store.run.stagnation_mode)

    def test_step_raises_after_converged_run(self):
        engine = build_engine()
        engine.run_until_stop(lambda store: accepted_improvement_proposal(engine, proposal_id=f"p_{store.run.iteration:04d}"))

        with self.assertRaises(RuntimeError):
            engine.step(make_proposal(engine, proposal_id="proposal_after_converged", delta={"budget": 9500}))

    def test_step_raises_after_halted_run(self):
        engine = build_engine(max_iterations=1)
        engine.step(make_proposal(engine, proposal_id="proposal_halt", delta={"title": ""}))

        with self.assertRaises(RuntimeError):
            engine.step(make_proposal(engine, proposal_id="proposal_after_halted", delta={"title": ""}))


if __name__ == "__main__":
    unittest.main()
