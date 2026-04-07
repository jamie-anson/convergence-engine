from __future__ import annotations

import unittest

from tests.helpers import accepted_improvement_proposal, build_engine, make_proposal


class EngineCountersAndModesTests(unittest.TestCase):
    def test_iteration_increments_for_every_evaluated_proposal_including_stale(self):
        engine = build_engine()
        engine.step(make_proposal(engine, proposal_id="proposal_reject", delta={"title": ""}))
        engine.step(make_proposal(engine, proposal_id="proposal_stale", based_on_state_version=99, delta={"title": "Ignored"}))

        self.assertEqual(2, engine.store.run.iteration)

    def test_no_improve_count_is_unchanged_for_stale(self):
        engine = build_engine()
        engine.store.run.no_improve_count = 2

        engine.step(make_proposal(engine, proposal_id="proposal_stale", based_on_state_version=99, delta={"title": "Ignored"}))

        self.assertEqual(2, engine.store.run.no_improve_count)

    def test_no_improve_count_resets_only_on_strict_improvement(self):
        engine = build_engine()
        engine.store.run.no_improve_count = 2

        evaluation = engine.step(accepted_improvement_proposal(engine, proposal_id="proposal_improve"))

        self.assertEqual("accept", evaluation.outcome)
        self.assertEqual(0, engine.store.run.no_improve_count)

    def test_no_improve_count_increments_on_reject_and_informative_reject(self):
        engine = build_engine()
        engine.step(make_proposal(engine, proposal_id="proposal_reject", delta={"title": "Better"}))
        self.assertEqual(1, engine.store.run.no_improve_count)

        engine.step(make_proposal(engine, proposal_id="proposal_informative", delta={"title": ""}))
        self.assertEqual(2, engine.store.run.no_improve_count)

    def test_allow_equal_accepts_equal_score_but_does_not_advance_best_state(self):
        engine = build_engine(allow_equal=True)
        first = make_proposal(
            engine,
            proposal_id="proposal_raise_title",
            delta={"title": "Long Enough"},
        )
        first_evaluation = engine.step(first)
        self.assertEqual("accept", first_evaluation.outcome)

        baseline_best = engine.store.run.best_state_version
        proposal = make_proposal(
            engine,
            proposal_id="proposal_equal",
            delta={"title": "Another Good"},
        )

        evaluation = engine.step(proposal)

        self.assertEqual("accept", evaluation.outcome)
        self.assertEqual("accepted_local", evaluation.reason)
        self.assertEqual(1, engine.store.run.no_improve_count)
        self.assertEqual(baseline_best, engine.store.run.best_state_version)

    def test_mode_transitions_happen_exactly_at_n1_and_n2(self):
        engine = build_engine(n1=2, n2=4)

        engine.step(make_proposal(engine, proposal_id="proposal_1", delta={"title": ""}))
        self.assertEqual("local", engine.store.run.stagnation_mode)

        engine.step(make_proposal(engine, proposal_id="proposal_2", delta={"title": ""}))
        self.assertEqual("exploration", engine.store.run.stagnation_mode)

        engine.step(make_proposal(engine, proposal_id="proposal_3", delta={"title": ""}))
        self.assertEqual("exploration", engine.store.run.stagnation_mode)

        engine.step(make_proposal(engine, proposal_id="proposal_4", delta={"title": ""}))
        self.assertEqual("halted", engine.store.run.stagnation_mode)
        self.assertEqual("halted", engine.store.run.status)

    def test_halting_by_stagnation_sets_status_and_mode(self):
        engine = build_engine(n1=1, n2=2, max_iterations=10)

        engine.step(make_proposal(engine, proposal_id="proposal_1", delta={"title": ""}))
        engine.step(make_proposal(engine, proposal_id="proposal_2", delta={"title": ""}))

        self.assertEqual("halted", engine.store.run.status)
        self.assertEqual("halted", engine.store.run.stagnation_mode)

    def test_halting_by_max_iterations_sets_status_and_mode(self):
        engine = build_engine(n1=10, n2=11, max_iterations=1)

        engine.step(make_proposal(engine, proposal_id="proposal_1", delta={"title": ""}))

        self.assertEqual("halted", engine.store.run.status)
        self.assertEqual("halted", engine.store.run.stagnation_mode)


if __name__ == "__main__":
    unittest.main()
