"""
End-to-end tests for classification.py: prompt text, and the full
load -> context -> prompt -> classify -> validate -> save pipeline for both
input formats and all three context modes.
"""
import unittest

from tests import FIXTURES_DIR
from classification_data import select_context, load_pipeline_processed
from classification import build_prompt, run, MockClassifier, ClassificationResult

MANUAL_PATH = FIXTURES_DIR / "tiny_manual.json"
PIPELINE_PATH = FIXTURES_DIR / "tiny_pipeline.json"                       # no docent_role at all (pre-Phase-4 file)
PIPELINE_ROLE_PATH = FIXTURES_DIR / "tiny_pipeline_with_docent_role.json"  # Phase-4-enriched


class TestBuildPrompt(unittest.TestCase):
    def test_prompt_shows_docent_role_per_turn(self):
        turns = load_pipeline_processed(PIPELINE_ROLE_PATH).turns
        window = select_context(turns, center_index=0, mode="B")
        prompt = build_prompt(window, "PLACEHOLDER_INDICATOR")
        self.assertIn("docent_role=DOCENT", prompt)

    def test_prompt_shows_onbekend_when_docent_role_missing(self):
        turns = load_pipeline_processed(PIPELINE_ROLE_PATH).turns
        window = select_context(turns, center_index=4, mode="A")  # docent_role=None
        prompt = build_prompt(window, "PLACEHOLDER_INDICATOR")
        self.assertIn("docent_role=ONBEKEND", prompt)


class TestRunEndToEnd(unittest.TestCase):
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
        for r in output["results"]:
            if r["status"] == "UNKNOWN":
                self.assertIsNone(r["detected"])

    def test_manual_results_flag_unknown_reliability(self):
        output = run(MANUAL_PATH, "B", ["PLACEHOLDER_INDICATOR"], MockClassifier())
        self.assertTrue(all(o["unknown_reliability"] for o in output["raw_outputs"]))

    def test_pipeline_results_use_known_reliability(self):
        output = run(PIPELINE_PATH, "A", ["PLACEHOLDER_INDICATOR"], MockClassifier())
        first = output["raw_outputs"][0]  # turn 0 in the fixture is clean
        self.assertFalse(first["unknown_reliability"])

    def test_reproducibility_record_has_required_fields(self):
        output = run(MANUAL_PATH, "C", ["PLACEHOLDER_INDICATOR"], MockClassifier())
        for key in ("input", "context_config", "prompt_version", "model_config",
                    "raw_outputs", "results", "errors"):
            self.assertIn(key, output)
        self.assertEqual(output["context_config"]["mode"], "C")
        self.assertEqual(output["model_config"]["name"], "mock")

    def test_full_route_with_docent_role_produces_no_errors(self):
        for mode in ("A", "B", "C"):
            with self.subTest(mode=mode):
                output = run(PIPELINE_ROLE_PATH, mode, ["PLACEHOLDER_INDICATOR"], MockClassifier())
                self.assertEqual(output["errors"], [])
                self.assertEqual(len(output["results"]), 5)

    def test_docent_role_unresolved_flag_present_in_raw_outputs(self):
        output = run(PIPELINE_ROLE_PATH, "A", ["PLACEHOLDER_INDICATOR"], MockClassifier())
        for entry in output["raw_outputs"]:
            self.assertIn("docent_role_unresolved", entry)

    def test_old_format_without_docent_role_still_works_end_to_end(self):
        """Backward compatibility: a Phase 3 file with no docent_role at all
        must still run through the exact same pipeline without errors."""
        output = run(PIPELINE_PATH, "B", ["PLACEHOLDER_INDICATOR"], MockClassifier())
        self.assertEqual(output["errors"], [])
        self.assertTrue(all(e["docent_role_unresolved"] for e in output["raw_outputs"]))  # all None -> all unresolved


if __name__ == "__main__":
    unittest.main()
