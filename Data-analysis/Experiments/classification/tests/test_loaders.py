"""STAP 7 tests: transcript loading (both formats), original input untouched,
missing speaker-uncertainty info treated as unknown (not reliable)."""
import json
import unittest

from tests import FIXTURES_DIR
from loaders import load_fragment, load_manual_fixture, load_pipeline_processed

MANUAL_PATH = FIXTURES_DIR / "tiny_manual.json"
PIPELINE_PATH = FIXTURES_DIR / "tiny_pipeline.json"


class TestManualLoader(unittest.TestCase):
    def test_loads_correct_turn_count_and_order(self):
        fragment = load_manual_fixture(MANUAL_PATH)
        self.assertEqual(fragment.fragment_id, "tiny_manual_fixture")
        self.assertEqual(fragment.source, "manual")
        self.assertEqual([t.turn_id for t in fragment.turns], [1, 2, 3, 4])
        self.assertEqual(fragment.turns[0].text, "Wat denk jij dat het antwoord is?")

    def test_missing_timestamps_do_not_break_loading(self):
        fragment = load_manual_fixture(MANUAL_PATH)
        self.assertTrue(all(t.start is None and t.end is None for t in fragment.turns))

    def test_missing_uncertainty_info_is_unknown_not_reliable(self):
        """Requirement: missing speaker-uncertainty info must be treated as
        UNKNOWN, never silently as 'reliable' (False)."""
        fragment = load_manual_fixture(MANUAL_PATH)
        for t in fragment.turns:
            self.assertIsNone(t.uncertain_assignment)
            self.assertIsNone(t.overlap)
            # explicitly NOT False — None and False must stay distinguishable
            self.assertIsNot(t.uncertain_assignment, False)
            self.assertIsNot(t.overlap, False)

    def test_speaker_mapping_preserved(self):
        fragment = load_manual_fixture(MANUAL_PATH)
        self.assertEqual(fragment.speaker_mapping, {"MAIN_SPEAKER": "DOCENT", "OTHER_SPEAKER": "LEERLING"})

    def test_original_input_file_not_modified(self):
        before = MANUAL_PATH.read_bytes()
        load_manual_fixture(MANUAL_PATH)
        after = MANUAL_PATH.read_bytes()
        self.assertEqual(before, after)


class TestPipelineLoader(unittest.TestCase):
    def test_loads_correct_turn_count(self):
        fragment = load_pipeline_processed(PIPELINE_PATH)
        self.assertEqual(fragment.source, "pipeline_processed")
        self.assertEqual([t.turn_id for t in fragment.turns], [0, 1, 2, 3])

    def test_timestamps_preserved(self):
        fragment = load_pipeline_processed(PIPELINE_PATH)
        self.assertEqual(fragment.turns[0].start, 0.0)
        self.assertEqual(fragment.turns[0].end, 3.0)

    def test_real_uncertainty_info_preserved_as_known_values(self):
        """Requirement: automated-pipeline uncertainty/overlap info must be
        kept, as the ACTUAL known True/False value — never reset to None."""
        fragment = load_pipeline_processed(PIPELINE_PATH)
        by_id = {t.turn_id: t for t in fragment.turns}
        self.assertEqual(by_id[1].uncertain_assignment, True)
        self.assertEqual(by_id[1].overlap, False)
        self.assertEqual(by_id[2].overlap, True)
        self.assertEqual(by_id[0].uncertain_assignment, False)
        self.assertEqual(by_id[0].overlap, False)

    def test_original_input_file_not_modified(self):
        before = PIPELINE_PATH.read_bytes()
        load_pipeline_processed(PIPELINE_PATH)
        after = PIPELINE_PATH.read_bytes()
        self.assertEqual(before, after)


class TestLoadFragmentDispatch(unittest.TestCase):
    """Both formats must go through the SAME downstream shape via one entry point."""

    def test_dispatches_manual_format(self):
        fragment = load_fragment(MANUAL_PATH)
        self.assertEqual(fragment.source, "manual")

    def test_dispatches_pipeline_format(self):
        fragment = load_fragment(PIPELINE_PATH)
        self.assertEqual(fragment.source, "pipeline_processed")

    def test_both_formats_produce_the_same_turn_shape(self):
        manual = load_fragment(MANUAL_PATH)
        pipeline = load_fragment(PIPELINE_PATH)
        manual_fields = set(manual.turns[0].model_dump().keys())
        pipeline_fields = set(pipeline.turns[0].model_dump().keys())
        self.assertEqual(manual_fields, pipeline_fields)

    def test_unrecognized_format_raises(self):
        bad_path = FIXTURES_DIR / "_unrecognized_tmp.json"
        bad_path.write_text(json.dumps({"nonsense": True}), encoding="utf-8")
        try:
            with self.assertRaises(ValueError):
                load_fragment(bad_path)
        finally:
            bad_path.unlink()


if __name__ == "__main__":
    unittest.main()
