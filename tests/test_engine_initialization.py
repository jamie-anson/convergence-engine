from __future__ import annotations

import unittest

from convergence_engine.utils import payload_hash
from examples.spec_refinement import score_spec_payload, validate_spec_payload
from tests.helpers import base_initial_payload, build_engine


class EngineInitializationTests(unittest.TestCase):
    def test_initialize_creates_expected_seeded_run_state(self):
        engine = build_engine()

        self.assertEqual("active", engine.store.run.status)
        self.assertEqual(0, engine.store.run.state_version)
        self.assertEqual(0, engine.store.run.best_state_version)
        self.assertEqual(0, engine.store.run.iteration)
        self.assertEqual(0, engine.store.run.no_improve_count)
        self.assertEqual("local", engine.store.run.stagnation_mode)
        self.assertEqual(1, len(engine.store.states))
        self.assertEqual(1, len(engine.store.accepted_hashes))

    def test_initialize_rejects_invalid_seed(self):
        invalid_payload = {
            "title": "",
            "problem": "too short",
            "solution": "too short",
            "budget": -1,
            "compliance": False,
        }

        with self.assertRaises(ValueError):
            from convergence_engine import ConvergenceEngineV1Lite

            ConvergenceEngineV1Lite.initialize(
                initial_payload=invalid_payload,
                validator=validate_spec_payload,
                scorer=score_spec_payload,
                threshold=0.55,
                exploration_floor=0.40,
                allow_equal=False,
                success_threshold=0.90,
                n1=3,
                n2=6,
                max_iterations=12,
            )

    def test_initialize_populates_initial_score_hash_and_best_state_deterministically(self):
        payload = base_initial_payload()
        engine = build_engine()
        initial_state = engine.store.current_state()

        self.assertEqual(payload, initial_state.payload)
        self.assertEqual(score_spec_payload(payload), initial_state.score)
        self.assertEqual(payload_hash(payload), initial_state.state_hash)
        self.assertIs(engine.store.best_state(), initial_state)
        self.assertEqual(initial_state.state_hash, next(iter(engine.store.accepted_hashes)))


if __name__ == "__main__":
    unittest.main()
