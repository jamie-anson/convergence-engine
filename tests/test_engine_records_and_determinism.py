from __future__ import annotations

import unittest

from examples.meeting_orchestrator import build_meeting_engine, orchestrator_proposal_generator
from examples.spec_refinement import build_demo_engine, deterministic_demo_proposal_generator
from tests.helpers import (
    accepted_improvement_proposal,
    assert_run_is_deterministic,
    assert_state_hash_matches_payload,
    build_engine,
    make_proposal,
)


class EngineRecordsAndDeterminismTests(unittest.TestCase):
    def test_accepted_proposal_appends_state_trail_evaluation_and_proposal(self):
        engine = build_engine()

        engine.step(accepted_improvement_proposal(engine, proposal_id="proposal_accept"))

        self.assertEqual(2, len(engine.store.states))
        self.assertEqual(1, len(engine.store.trail))
        self.assertEqual(1, len(engine.store.evaluations))
        self.assertEqual(1, len(engine.store.proposals))
        self.assertEqual("trail_0000", engine.store.trail[0].trail_id)
        assert_state_hash_matches_payload(self, engine)

    def test_rejected_and_stale_proposals_append_only_evaluation_and_proposal(self):
        engine = build_engine()
        engine.step(make_proposal(engine, proposal_id="proposal_reject", delta={"title": "Better"}))
        engine.step(make_proposal(engine, proposal_id="proposal_stale", based_on_state_version=99, delta={"title": "Ignored"}))

        self.assertEqual(1, len(engine.store.states))
        self.assertEqual(0, len(engine.store.trail))
        self.assertEqual(2, len(engine.store.evaluations))
        self.assertEqual(2, len(engine.store.proposals))

    def test_current_state_and_best_state_track_run_correctly(self):
        engine = build_engine()
        engine.step(accepted_improvement_proposal(engine, proposal_id="proposal_accept"))

        self.assertEqual(1, engine.store.current_state().state_version)
        self.assertEqual(engine.store.current_state().state_version, engine.store.best_state().state_version)

    def test_generated_ids_are_deterministic_within_a_run(self):
        engine = build_engine()
        engine.step(accepted_improvement_proposal(engine, proposal_id="proposal_accept"))
        engine.step(make_proposal(engine, proposal_id="proposal_bad_1", based_on_state_version=1, delta={"title": ""}))

        self.assertEqual("eval_0000", engine.store.evaluations[0].evaluation_id)
        self.assertEqual("trail_0000", engine.store.trail[0].trail_id)
        self.assertEqual("eval_0001", engine.store.evaluations[1].evaluation_id)
        self.assertEqual("constraint_0000", engine.store.constraints[0].constraint_id)

    def test_identical_runs_serialize_to_identical_canonical_json(self):
        engine_one = build_demo_engine()
        engine_two = build_demo_engine()

        engine_one.run_until_stop(deterministic_demo_proposal_generator)
        engine_two.run_until_stop(deterministic_demo_proposal_generator)

        assert_run_is_deterministic(self, engine_one, engine_two)

    def test_spec_refinement_example_reaches_expected_best_state(self):
        engine = build_demo_engine()
        engine.run_until_stop(deterministic_demo_proposal_generator)
        best = engine.store.best_state()

        self.assertEqual(9500, best.payload["budget"])
        self.assertTrue(best.payload["compliance"])
        self.assertGreaterEqual(best.score, 0.90)

    def test_meeting_example_reaches_conflict_free_selection(self):
        engine = build_meeting_engine()
        engine.run_until_stop(orchestrator_proposal_generator)
        best = engine.store.best_state()

        self.assertEqual("2026-04-08T15:00:00Z", best.payload["selected_slot"])
        self.assertEqual(0, best.payload["conflicts"])
        self.assertGreaterEqual(best.score, 0.95)


if __name__ == "__main__":
    unittest.main()
