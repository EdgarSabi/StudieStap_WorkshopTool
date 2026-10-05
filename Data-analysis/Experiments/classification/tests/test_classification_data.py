"""
Tests for classification_data.py: loading both transcript formats, context
window selection, the ClassificationResult schema, and docent_role
passthrough at the data level (loading + context, not prompt text — see
test_classification.py for that).
"""
import json
import unittest

from tests import FIXTURES_DIR
from pydantic import ValidationError
from classification_data import (
    load_fragment, load_manual_fixture, load_pipeline_processed,
    select_context, iter_context_windows, ClassificationResult,
)

MANUAL_PATH = FIXTURES_DIR / "tiny_manual.json"
PIPELINE_PATH = FIXTURES_DIR / "tiny_pipeline.json"                       # no docent_role at all (pre-Phase-4 file)
PIPELINE_ROLE_PATH = FIXTURES_DIR / "tiny_pipeline_with_docent_role.json"  # Phase-4-enriched


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
            self.assertIsNot(t.uncertain_assignment, False)
            self.assertIsNot(t.overlap, False)

    def test_speaker_mapping_preserved(self):
        fragment = load_manual_fixture(MANUAL_PATH)
        self.assertEqual(fragment.speaker_mapping, {"MAIN_SPEAKER": "DOCENT", "OTHER_SPEAKER": "LEERLING"})

    def test_original_input_file_not_modified(self):
        before = MANUAL_PATH.read_bytes()
        load_manual_fixture(MANUAL_PATH)
        self.assertEqual(before, MANUAL_PATH.read_bytes())

    def test_manual_transcript_never_gets_a_docent_role(self):
        """speaker_mapping is informational only — never wired into docent_role."""
        fragment = load_manual_fixture(MANUAL_PATH)
        self.assertIsNotNone(fragment.speaker_mapping)  # the mapping IS present...
        self.assertTrue(all(t.docent_role is None for t in fragment.turns))  # ...but never used as a role


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
        self.assertEqual(before, PIPELINE_PATH.read_bytes())

    def test_pre_phase4_file_has_no_docent_role_at_all(self):
        """Old Phase 3 output (before docent recognition existed) must still
        load fine, with docent_role simply absent/None everywhere."""
        fragment = load_pipeline_processed(PIPELINE_PATH)
        self.assertTrue(all(t.docent_role is None for t in fragment.turns))


class TestDocentRolePassthrough(unittest.TestCase):
    """docent_role/similarity/note flow unchanged from SpeakerTurn ->
    ClassificationTurn: missing recognition stays None (never inferred from
    `speaker`), mixed speech (overlap) stays ONZEKER, and different
    OTHER-speakers are never conflated just because they share a role."""

    def setUp(self):
        self.by_id = {t.turn_id: t for t in load_pipeline_processed(PIPELINE_ROLE_PATH).turns}

    def test_docent_role_carried_over_unchanged(self):
        self.assertEqual(self.by_id[0].docent_role, "DOCENT")
        self.assertEqual(self.by_id[0].docent_role_similarity, 0.6)

    def test_different_other_speakers_keep_separate_identity(self):
        """Requirement: don't conflate different raw speakers just because
        both ended up with docent_role=OTHER."""
        t1, t2 = self.by_id[1], self.by_id[2]
        self.assertEqual(t1.docent_role, "OTHER")
        self.assertEqual(t2.docent_role, "OTHER")
        self.assertNotEqual(t1.speaker, t2.speaker)  # OTHER_SPEAKER_1 vs OTHER_SPEAKER_2 — never merged

    def test_mixed_speech_stays_onzeker_with_no_similarity(self):
        """Requirement: 'gemengde spraak' (overlap) must not be silently
        treated as reliable evidence for a role."""
        t3 = self.by_id[3]
        self.assertTrue(t3.overlap)
        self.assertEqual(t3.docent_role, "ONZEKER")
        self.assertIsNone(t3.docent_role_similarity)
        self.assertIsNotNone(t3.docent_role_note)

    def test_missing_recognition_stays_unknown_not_inferred_from_main_speaker(self):
        """Requirement: MAIN_SPEAKER does not automatically mean DOCENT."""
        t4 = self.by_id[4]
        self.assertEqual(t4.speaker, "MAIN_SPEAKER")
        self.assertIsNone(t4.docent_role)
        self.assertIsNone(t4.docent_role_similarity)


class TestLoadFragmentDispatch(unittest.TestCase):
    """Both formats must go through the SAME downstream shape via one entry point."""

    def test_dispatches_manual_format(self):
        self.assertEqual(load_fragment(MANUAL_PATH).source, "manual")

    def test_dispatches_pipeline_format(self):
        self.assertEqual(load_fragment(PIPELINE_PATH).source, "pipeline_processed")

    def test_dispatches_docent_role_enriched_file(self):
        fragment = load_fragment(PIPELINE_ROLE_PATH)
        self.assertEqual(fragment.source, "pipeline_processed")
        self.assertEqual(len(fragment.turns), 5)

    def test_both_formats_produce_the_same_turn_shape(self):
        manual_fields = set(load_fragment(MANUAL_PATH).turns[0].model_dump().keys())
        pipeline_fields = set(load_fragment(PIPELINE_PATH).turns[0].model_dump().keys())
        self.assertEqual(manual_fields, pipeline_fields)

    def test_unrecognized_format_raises(self):
        bad_path = FIXTURES_DIR / "_unrecognized_tmp.json"
        bad_path.write_text(json.dumps({"nonsense": True}), encoding="utf-8")
        try:
            with self.assertRaises(ValueError):
                load_fragment(bad_path)
        finally:
            bad_path.unlink()


class TestSelectContext(unittest.TestCase):
    def setUp(self):
        self.turns = load_manual_fixture(MANUAL_PATH).turns  # turn_ids 1,2,3,4

    def test_mode_A_only_current_turn(self):
        window = select_context(self.turns, center_index=1, mode="A")  # turn_id 2
        self.assertEqual(window.center_turn_id, 2)
        self.assertEqual(window.context_turn_ids, [2])

    def test_mode_B_previous_plus_current(self):
        window = select_context(self.turns, center_index=2, mode="B")  # turn_id 3
        self.assertEqual(window.center_turn_id, 3)
        self.assertEqual(window.context_turn_ids, [2, 3])

    def test_mode_B_clips_at_start(self):
        window = select_context(self.turns, center_index=0, mode="B")  # turn_id 1, no previous
        self.assertEqual(window.context_turn_ids, [1])

    def test_mode_C_two_previous_plus_current_plus_next(self):
        window = select_context(self.turns, center_index=2, mode="C")  # turn_id 3
        self.assertEqual(window.center_turn_id, 3)
        self.assertEqual(window.context_turn_ids, [1, 2, 3, 4])

    def test_mode_C_clips_at_end(self):
        window = select_context(self.turns, center_index=3, mode="C")  # turn_id 4, last turn, no next
        self.assertEqual(window.context_turn_ids, [2, 3, 4])

    def test_center_always_included_in_context(self):
        for mode in ("A", "B", "C"):
            for i in range(len(self.turns)):
                window = select_context(self.turns, center_index=i, mode=mode)
                self.assertIn(window.center_turn_id, window.context_turn_ids)

    def test_unknown_mode_raises(self):
        with self.assertRaises(ValueError):
            select_context(self.turns, center_index=0, mode="Z")

    def test_out_of_range_index_raises(self):
        with self.assertRaises(IndexError):
            select_context(self.turns, center_index=99, mode="A")


class TestIterContextWindows(unittest.TestCase):
    def test_one_window_per_turn_no_duplicates(self):
        turns = load_manual_fixture(MANUAL_PATH).turns
        for mode in ("A", "B", "C"):
            windows = list(iter_context_windows(turns, mode))
            self.assertEqual(len(windows), len(turns))
            centers = [w.center_turn_id for w in windows]
            self.assertEqual(centers, [1, 2, 3, 4])
            self.assertEqual(len(centers), len(set(centers)))  # never the same turn twice as center


class TestReliabilityFlags(unittest.TestCase):
    def test_manual_turns_are_unknown_reliability(self):
        turns = load_manual_fixture(MANUAL_PATH).turns
        window = select_context(turns, center_index=1, mode="B")
        self.assertTrue(window.unknown_reliability)
        self.assertFalse(window.flagged_uncertain)  # None != True

    def test_pipeline_turns_use_real_flags(self):
        turns = load_pipeline_processed(PIPELINE_PATH).turns  # turn 1: uncertain_assignment=True
        window = select_context(turns, center_index=1, mode="A")
        self.assertFalse(window.unknown_reliability)
        self.assertTrue(window.flagged_uncertain)

    def test_pipeline_clean_turn_is_known_and_not_flagged(self):
        turns = load_pipeline_processed(PIPELINE_PATH).turns  # turn 0: overlap=False, uncertain_assignment=False
        window = select_context(turns, center_index=0, mode="A")
        self.assertFalse(window.unknown_reliability)
        self.assertFalse(window.flagged_uncertain)

    def test_docent_role_unresolved_false_for_clean_resolved_window(self):
        turns = load_pipeline_processed(PIPELINE_ROLE_PATH).turns
        # turn 1 (index 1): window B = [turn0, turn1], both resolved (DOCENT, OTHER)
        window = select_context(turns, center_index=1, mode="B")
        self.assertFalse(window.docent_role_unresolved)

    def test_docent_role_unresolved_true_when_onzeker_turn_in_window(self):
        turns = load_pipeline_processed(PIPELINE_ROLE_PATH).turns
        window = select_context(turns, center_index=3, mode="A")  # turn 3 = ONZEKER
        self.assertTrue(window.docent_role_unresolved)

    def test_docent_role_unresolved_true_when_missing_turn_in_window(self):
        turns = load_pipeline_processed(PIPELINE_ROLE_PATH).turns
        window = select_context(turns, center_index=4, mode="A")  # turn 4 = docent_role None
        self.assertTrue(window.docent_role_unresolved)


def _base_result_kwargs(**overrides):
    kwargs = dict(
        fragment_id="tiny_manual_fixture",
        center_turn_id=2,
        context_turn_ids=[1, 2],
        indicator_id="PLACEHOLDER_INDICATOR",
        detected=True,
        evidence="fixed mock evidence",
        status="OK",
        model_name="mock",
        model_version="0.1",
        prompt_version="placeholder-v0",
    )
    kwargs.update(overrides)
    return kwargs


class TestClassificationResultSchema(unittest.TestCase):
    def test_valid_ok_result(self):
        result = ClassificationResult(**_base_result_kwargs())
        self.assertEqual(result.status, "OK")
        self.assertTrue(result.detected)

    def test_unknown_status_allows_none_detected_and_evidence(self):
        result = ClassificationResult(**_base_result_kwargs(status="UNKNOWN", detected=None, evidence=None))
        self.assertEqual(result.status, "UNKNOWN")
        self.assertIsNone(result.detected)

    def test_invalid_status_rejected(self):
        with self.assertRaises(ValidationError):
            ClassificationResult(**_base_result_kwargs(status="MAYBE"))

    def test_center_turn_must_be_in_context_turn_ids(self):
        with self.assertRaises(ValidationError):
            ClassificationResult(**_base_result_kwargs(center_turn_id=99, context_turn_ids=[1, 2]))

    def test_missing_required_field_rejected(self):
        kwargs = _base_result_kwargs()
        del kwargs["model_name"]
        with self.assertRaises(ValidationError):
            ClassificationResult(**kwargs)


if __name__ == "__main__":
    unittest.main()
