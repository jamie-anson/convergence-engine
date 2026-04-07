from __future__ import annotations

import json
import unittest

from convergence_engine import (
    SchemaValidationError,
    assert_valid_named_schema,
    load_schema,
    serialize_engine,
    serialize_store,
    to_json,
    validate_named_schema,
)
from examples.spec_refinement import build_demo_engine, deterministic_demo_proposal_generator


class PublicApiAndSerializationTests(unittest.TestCase):
    def test_load_schema_reads_packaged_schema_assets(self):
        schema = load_schema("engine_run")
        self.assertEqual("engine_run", schema["$id"])
        self.assertEqual("object", schema["type"])

    def test_validate_named_schema_accepts_valid_runtime_object(self):
        engine = build_demo_engine()
        errors = validate_named_schema(engine.store.run, "engine_run")
        self.assertEqual([], errors)

    def test_assert_valid_named_schema_raises_on_invalid_object(self):
        with self.assertRaises(SchemaValidationError):
            assert_valid_named_schema({"run_id": "missing-most-fields"}, "engine_run")

    def test_serialize_engine_and_store_return_same_plain_artifact(self):
        engine = build_demo_engine()
        engine.run_until_stop(deterministic_demo_proposal_generator)

        self.assertEqual(serialize_engine(engine), serialize_store(engine.store))
        self.assertIn("run", serialize_engine(engine))
        self.assertIn("states", serialize_engine(engine))

    def test_to_json_outputs_valid_json_with_expected_top_level_keys(self):
        engine = build_demo_engine()
        engine.run_until_stop(deterministic_demo_proposal_generator)

        payload = json.loads(to_json(serialize_engine(engine)))
        self.assertIn("run", payload)
        self.assertIn("evaluations", payload)
        self.assertEqual(engine.store.run.run_id, payload["run"]["run_id"])


if __name__ == "__main__":
    unittest.main()
