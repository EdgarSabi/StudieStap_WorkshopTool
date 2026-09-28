"""
Tests for Phase 4 (docent recognition) integration: docent_role/similarity/
note flow unchanged from SpeakerTurn -> ClassificationTurn -> ContextWindow
-> prompt, missing recognition stays None (never inferred from `speaker`),
mixed speech (overlap) stays ONZEKER, and different OTHER-speakers are never
conflated just because they share a role.
"""
import unittest

from tests import FIXTURES_DIR
from loaders import load_fragment, load_manual_fixture, load_pipeline_processed
from context.selector import select_context
from classifiers.prompt import build_prompt
from run_classification import run
from classifiers.mock import MockClassifier

MANUAL_PATH = FIXTURES_DIR / "tiny_manual.json"
PIPELINE_PATH = FIXTURES_DIR / "tiny_pipeline.json"                       # no docent_role at all (pre-Phase-4 file)
PIPELINE_ROLE_PATH = FIXTURES_DIR / "tiny_pipeline_with_docent_role.json"  # Phase-4-enriched


class TestDocentRolePassthrough(unittest.TestCase):
    def setUp(self):
        self.fragment = load_pipeline_processed(PIPELINE_ROLE_PATH)
        self.by_id = {t.turn_id: t for t in self.fragment.turns}

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

    def test_pre_phase4_file_has_no_docent_role_at_all(self):
        """Old Phase 3 output (before docent recognition existed) must still
        load fine, with docent_role simply absent/None everywhere."""
        fragment = load_pipeline_processed(PIPELINE_PATH)
        self.assertTrue(all(t.docent_role is None for t in fragment.turns))

    def test_manual_transcript_never_gets_a_docent_role(self):
        """speaker_mapping is informational only — never wired into docent_role."""
        fragment = load_manual_fixture(MANUAL_PATH)
        self.assertIsNotNone(fragment.speaker_mapping)  # the mapping IS present...
        self.assertTrue(all(t.docent_role is None for t in fragment.turns))  # ...but never used as a role

    def test_load_fragment_dispatch_still_works_for_enriched_file(self):
        fragment = load_fragment(PIPELINE_ROLE_PATH)
        self.assertEqual(fragment.source, "pipeline_processed")
        self.assertEqual(len(fragment.turns), 5)


class TestDocentRoleInContextAndPrompt(unittest.TestCase):
    def setUp(self):
        self.turns = load_pipeline_processed(PIPELINE_ROLE_PATH).turns

    def test_docent_role_unresolved_false_for_clean_resolved_window(self):
        # turn 1 (index 1): window B = [turn0, turn1], both resolved (DOCENT, OTHER)
        window = select_context(self.turns, center_index=1, mode="B")
        self.assertFalse(window.docent_role_unresolved)

    def test_docent_role_unresolved_true_when_onzeker_turn_in_window(self):
        # turn 3 (index 3, ONZEKER) as center
        window = select_context(self.turns, center_index=3, mode="A")
        self.assertTrue(window.docent_role_unresolved)

    def test_docent_role_unresolved_true_when_missing_turn_in_window(self):
        # turn 4 (index 4, docent_role=None) as center
        window = select_context(self.turns, center_index=4, mode="A")
        self.assertTrue(window.docent_role_unresolved)

    def test_prompt_shows_docent_role_per_turn(self):
        window = select_context(self.turns, center_index=0, mode="B")
        prompt = build_prompt(window, "PLACEHOLDER_INDICATOR")
        self.assertIn("docent_role=DOCENT", prompt)

    def test_prompt_shows_onbekend_when_docent_role_missing(self):
        window = select_context(self.turns, center_index=4, mode="A")
        prompt = build_prompt(window, "PLACEHOLDER_INDICATOR")
        self.assertIn("docent_role=ONBEKEND", prompt)


class TestDocentRoleEndToEnd(unittest.TestCase):
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
