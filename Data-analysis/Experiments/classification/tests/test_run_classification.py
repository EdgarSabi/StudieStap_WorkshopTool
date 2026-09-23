"""STAP 7 end-to-end smoke test: both input formats through the SAME
pipeline (loader -> context -> prompt -> mock classifier -> schema
validation), for all three context modes, with no errors."""
import unittest

from tests import FIXTURES_DIR
from run_classification import run
from classifiers.mock import MockClassifier
from schemas.result import ClassificationResult

MANUAL_PATH = FIXTURES_DIR / "tiny_manual.json"
PIPELINE_PATH = FIXTURES_DIR / "tiny_pipeline.json"


class TestRunClassificationEndToEnd(unittest.TestCase):
    def test_manual_fixture_all_modes(self):
        for mode in ("A", "B", "C"):
            with self.subTest(mode=mode):
                output = run(MANUAL_PATH, mode, ["PLACEHOLDER_INDICATOR"], MockClassifier())
                self.assertEqual(len(output["results"]), 4)  # 1 result per turn, never duplicated
                self.assertEqual(output["errors"], [])
                for r in output["results"]:
                    ClassificationResult(**r)  # re-validates the already-dumped result

    def test_pipeline_fixture_same_pipeline(self):
        output = run(PIPELINE_PATH, "B", ["PLACEHOLDER_INDICATOR"], MockClassifier())
        self.assertEqual(output["input"]["source_format"], "pipeline_processed")
        self.assertEqual(len(output["results"]), 4)
        self.assertEqual(output["errors"], [])

    def test_unknown_status_is_handled_not_dropped(self):
        # MockClassifier's 3rd canned result is UNKNOWN; 4 turns -> it's hit at least once.
        output = run(MANUAL_PATH, "A", ["PLACEHOLDER_INDICATOR"], MockClassifier())
        statuses = [r["status"] for r in output["results"]]
        self.assertIn("UNKNOWN", statuses)
        unknown_results = [r for r in output["results"] if r["status"] == "UNKNOWN"]
        for r in unknown_results:
            self.assertIsNone(r["detected"])

    def test_manual_results_flag_unknown_reliability(self):
        output = run(MANUAL_PATH, "B", ["PLACEHOLDER_INDICATOR"], MockClassifier())
        self.assertTrue(all(o["unknown_reliability"] for o in output["raw_outputs"]))

    def test_pipeline_results_use_known_reliability(self):
        output = run(PIPELINE_PATH, "A", ["PLACEHOLDER_INDICATOR"], MockClassifier())
        # turn 0 in the fixture is clean (overlap=False, uncertain_assignment=False)
        first = output["raw_outputs"][0]
        self.assertFalse(first["unknown_reliability"])

    def test_reproducibility_record_has_required_fields(self):
        output = run(MANUAL_PATH, "C", ["PLACEHOLDER_INDICATOR"], MockClassifier())
        for key in ("input", "context_config", "prompt_version", "model_config",
                    "raw_outputs", "results", "errors"):
            self.assertIn(key, output)
        self.assertEqual(output["context_config"]["mode"], "C")
        self.assertEqual(output["model_config"]["name"], "mock")


if __name__ == "__main__":
    unittest.main()
