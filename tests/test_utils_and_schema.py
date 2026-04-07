from __future__ import annotations

import json
import unittest
from dataclasses import asdict

from convergence_engine.utils import canonical_json, merge_patch, payload_hash
from examples.spec_refinement import build_demo_engine, deterministic_demo_proposal_generator
from tests.helpers import ROOT, assert_matches_schema_shape, load_schema


class UtilsAndSchemaTests(unittest.TestCase):
    def test_merge_patch_handles_nested_replacement_and_deletion_without_mutation(self):
        original = {"a": {"b": 1, "c": 2}, "d": {"e": 3}, "f": 4}
        patch = {"a": {"b": 9}, "d": None}

        result = merge_patch(original, patch)

        self.assertEqual({"a": {"b": 9, "c": 2}, "f": 4}, result)
        self.assertEqual({"a": {"b": 1, "c": 2}, "d": {"e": 3}, "f": 4}, original)

    def test_merge_patch_replaces_target_when_patch_is_not_an_object(self):
        original = {"a": 1}
        result = merge_patch(original, ["replacement"])

        self.assertEqual(["replacement"], result)
        self.assertEqual({"a": 1}, original)

    def test_canonical_json_is_stable_for_dict_orderings_and_dataclasses(self):
        left = {"b": 2, "a": {"d": 4, "c": 3}}
        right = {"a": {"c": 3, "d": 4}, "b": 2}
        engine = build_demo_engine()

        self.assertEqual(canonical_json(left), canonical_json(right))
        self.assertEqual(canonical_json(engine.store.run), canonical_json(asdict(engine.store.run)))

    def test_payload_hash_is_stable(self):
        payload = {"b": 2, "a": {"d": 4, "c": 3}}
        same_payload = {"a": {"c": 3, "d": 4}, "b": 2}

        self.assertEqual(payload_hash(payload), payload_hash(same_payload))

    def test_machine_readable_schema_files_are_valid_json_objects(self):
        schema_dir = ROOT / "schemas" / "v1-lite"
        for schema_file in schema_dir.glob("*.json"):
            data = json.loads(schema_file.read_text())
            self.assertIn("$id", data)
            self.assertEqual("object", data["type"])

    def test_runtime_objects_match_checked_in_schema_shapes(self):
        engine = build_demo_engine()
        engine.run_until_stop(deterministic_demo_proposal_generator)

        assert_matches_schema_shape(self, engine.store.run, load_schema("engine_run"))
        for state in engine.store.states:
            assert_matches_schema_shape(self, state, load_schema("state"))
        for proposal in engine.store.proposals:
            assert_matches_schema_shape(self, proposal, load_schema("proposal"))
        for constraint in engine.store.constraints:
            assert_matches_schema_shape(self, constraint, load_schema("constraint"))
        for evaluation in engine.store.evaluations:
            assert_matches_schema_shape(self, evaluation, load_schema("evaluation"))
        for trail_entry in engine.store.trail:
            assert_matches_schema_shape(self, trail_entry, load_schema("trail_entry"))


if __name__ == "__main__":
    unittest.main()
