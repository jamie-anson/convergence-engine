from __future__ import annotations

import unittest

from convergence_engine import Constraint
from tests.helpers import accepted_improvement_proposal, build_engine, make_proposal


class EngineConstraintTests(unittest.TestCase):
    def test_equals_constraint_is_enforced(self):
        engine = build_engine()
        engine.store.constraints.append(
            Constraint("constraint_equals", engine.store.run.run_id, "title", "equals", "Blocked", 0)
        )

        evaluation = engine.step(
            make_proposal(
                engine,
                proposal_id="proposal_equals",
                delta={"title": "Blocked"},
            )
        )

        self.assertEqual("reject_informative", evaluation.outcome)
        self.assertEqual("constraint_violated:title:equals", evaluation.reason)

    def test_not_equals_constraint_is_enforced(self):
        engine = build_engine()
        engine.store.constraints.append(
            Constraint("constraint_not_equals", engine.store.run.run_id, "title", "not_equals", "Spec", 0)
        )

        evaluation = engine.step(
            make_proposal(engine, proposal_id="proposal_not_equals", delta={"title": "Refined Product Specification"})
        )

        self.assertEqual("reject_informative", evaluation.outcome)
        self.assertEqual("constraint_violated:title:not_equals", evaluation.reason)

    def test_greater_constraint_is_enforced(self):
        engine = build_engine()
        engine.store.constraints.append(
            Constraint("constraint_greater", engine.store.run.run_id, "budget", "greater", 10000, 0)
        )

        evaluation = engine.step(
            make_proposal(
                engine,
                proposal_id="proposal_greater",
                delta={
                    "budget": 12000,
                    "solution": "This is now long enough to satisfy the domain validation requirement.",
                },
            )
        )

        self.assertEqual("reject_informative", evaluation.outcome)
        self.assertEqual("constraint_violated:budget:greater", evaluation.reason)

    def test_less_constraint_is_enforced(self):
        engine = build_engine()
        engine.store.constraints.append(
            Constraint("constraint_less", engine.store.run.run_id, "budget", "less", 20000, 0)
        )

        evaluation = engine.step(
            make_proposal(engine, proposal_id="proposal_less", delta={"budget": 15000})
        )

        self.assertEqual("reject_informative", evaluation.outcome)
        self.assertEqual("constraint_violated:budget:less", evaluation.reason)

    def test_invalid_constraint_is_enforced(self):
        engine = build_engine()
        engine.store.constraints.append(
            Constraint("constraint_invalid", engine.store.run.run_id, "title", "invalid", None, 0)
        )

        evaluation = engine.step(
            make_proposal(engine, proposal_id="proposal_invalid_constraint", delta={"budget": 9500})
        )

        self.assertEqual("reject_informative", evaluation.outcome)
        self.assertEqual("constraint_violated:title:invalid", evaluation.reason)

    def test_missing_constraint_path_is_ignored(self):
        engine = build_engine()
        engine.store.constraints.append(
            Constraint("constraint_missing", engine.store.run.run_id, "missing.nested.path", "invalid", None, 0)
        )

        evaluation = engine.step(accepted_improvement_proposal(engine, proposal_id="proposal_missing_path"))

        self.assertEqual("accept", evaluation.outcome)
        self.assertEqual(1, engine.store.run.state_version)

    def test_reject_informative_creates_exactly_one_constraint_with_expected_fields(self):
        engine = build_engine()
        evaluation = engine.step(make_proposal(engine, proposal_id="proposal_bad", delta={"title": ""}))

        self.assertEqual("reject_informative", evaluation.outcome)
        self.assertEqual(1, len(engine.store.constraints))
        constraint = engine.store.constraints[0]
        self.assertEqual("title", constraint.field)
        self.assertEqual("invalid", constraint.operator)
        self.assertIsNone(constraint.value)
        self.assertEqual(0, constraint.state_version)

    def test_non_informative_rejections_do_not_create_constraints(self):
        engine = build_engine()
        before = len(engine.store.constraints)
        engine.step(make_proposal(engine, proposal_id="proposal_weak", delta={"title": "Better"}))
        engine.step(make_proposal(engine, proposal_id="proposal_stale", based_on_state_version=99, delta={"title": "Ignored"}))

        self.assertEqual(before, len(engine.store.constraints))


if __name__ == "__main__":
    unittest.main()
