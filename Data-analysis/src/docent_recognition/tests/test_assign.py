"""
Tests for docent_recognition/assign.py's decision rule. Uses a fake
recognizer (no real pyannote model, no HF_TOKEN, no audio needed) so these
run fast and don't depend on network/model downloads — only the pure
decision logic in assign_docent_roles() is under test here.
"""
import unittest
from typing import Optional

import torch

from config import DocentRecognitionConfig
from models.processed import SpeakerTurn
from docent_recognition.assign import assign_docent_roles, ROLE_DOCENT, ROLE_OTHER, ROLE_ONZEKER

SAMPLE_RATE = 16000
DUMMY_WAVEFORM = torch.zeros((1, SAMPLE_RATE * 60))  # 60s of silence — long enough for any test turn


class FakeRecognizer:
    """Stand-in for DocentReferenceRecognizer: returns a fixed
    (similarity, warning) pair and records how many times it was called, so
    tests can assert embedding was (or wasn't) attempted at all."""

    def __init__(self, similarity: Optional[float], warning: Optional[str] = None):
        self.similarity = similarity
        self.warning = warning
        self.call_count = 0

    def similarity_to_reference(self, waveform: torch.Tensor, sample_rate: int):
        self.call_count += 1
        return self.similarity, self.warning


def make_turn(turn_id: int, start: float, end: float, *, overlap: bool = False, uncertain_assignment: bool = False) -> SpeakerTurn:
    return SpeakerTurn(
        turn_id=turn_id, speaker="MAIN_SPEAKER", start=start, end=end, text=f"turn {turn_id}",
        overlap=overlap, uncertain_assignment=uncertain_assignment,
    )


def make_config(threshold: float = 0.35, min_duration: float = 1.0) -> DocentRecognitionConfig:
    return DocentRecognitionConfig(
        reference_audio="fictief_docent_ref.mp3",
        similarity_threshold=threshold,
        min_clip_duration_seconds=min_duration,
    )


class TestUncertainAssignmentAlwaysBlocks(unittest.TestCase):
    def test_uncertain_assignment_true_forces_onzeker_without_embedding(self):
        """Rule 1: uncertain_assignment=True -> ONZEKER, and the embedding
        step must not even be attempted (the label can't be trusted
        regardless of what the embedding would say)."""
        turn = make_turn(0, 0.0, 5.0, overlap=False, uncertain_assignment=True)
        recognizer = FakeRecognizer(similarity=0.9)  # would clearly say DOCENT if it were ever called
        [result] = assign_docent_roles([turn], DUMMY_WAVEFORM, SAMPLE_RATE, recognizer, make_config())

        self.assertEqual(result.docent_role, ROLE_ONZEKER)
        self.assertIsNone(result.docent_role_similarity)
        self.assertEqual(recognizer.call_count, 0, "embedding must not be computed when uncertain_assignment=True")

    def test_uncertain_assignment_true_wins_even_if_overlap_is_also_true(self):
        turn = make_turn(0, 0.0, 5.0, overlap=True, uncertain_assignment=True)
        recognizer = FakeRecognizer(similarity=0.9)
        [result] = assign_docent_roles([turn], DUMMY_WAVEFORM, SAMPLE_RATE, recognizer, make_config())

        self.assertEqual(result.docent_role, ROLE_ONZEKER)
        self.assertEqual(recognizer.call_count, 0)


class TestOverlapNoLongerBlocksRecognition(unittest.TestCase):
    """The behaviour change this update introduces: overlap=True alone no
    longer forces ONZEKER — a clip with a clear dominant voice can still be
    embedded and get a real DOCENT/OTHER label."""

    def test_overlap_true_with_clear_high_similarity_gives_docent(self):
        turn = make_turn(0, 0.0, 5.0, overlap=True, uncertain_assignment=False)
        recognizer = FakeRecognizer(similarity=0.8)
        [result] = assign_docent_roles([turn], DUMMY_WAVEFORM, SAMPLE_RATE, recognizer, make_config(threshold=0.35))

        self.assertEqual(result.docent_role, ROLE_DOCENT)
        self.assertEqual(result.docent_role_similarity, 0.8)
        self.assertEqual(recognizer.call_count, 1, "embedding SHOULD be computed when only overlap=True")

    def test_overlap_true_with_clear_low_similarity_gives_other(self):
        turn = make_turn(0, 0.0, 5.0, overlap=True, uncertain_assignment=False)
        recognizer = FakeRecognizer(similarity=0.05)
        [result] = assign_docent_roles([turn], DUMMY_WAVEFORM, SAMPLE_RATE, recognizer, make_config(threshold=0.35))

        self.assertEqual(result.docent_role, ROLE_OTHER)
        self.assertEqual(result.docent_role_similarity, 0.05)

    def test_overlap_true_still_recorded_as_a_warning_in_the_note(self):
        turn = make_turn(0, 0.0, 5.0, overlap=True, uncertain_assignment=False)
        recognizer = FakeRecognizer(similarity=0.8)
        [result] = assign_docent_roles([turn], DUMMY_WAVEFORM, SAMPLE_RATE, recognizer, make_config())

        self.assertIsNotNone(result.docent_role_note)
        self.assertIn("overlap", result.docent_role_note.lower())

    def test_overlap_false_gives_no_overlap_warning(self):
        """Sanity check: the overlap caution must only appear when overlap
        is actually True, not unconditionally on every resolved turn."""
        turn = make_turn(0, 0.0, 5.0, overlap=False, uncertain_assignment=False)
        recognizer = FakeRecognizer(similarity=0.8, warning=None)
        [result] = assign_docent_roles([turn], DUMMY_WAVEFORM, SAMPLE_RATE, recognizer, make_config())

        self.assertIsNone(result.docent_role_note)


class TestOtherRulesUnchanged(unittest.TestCase):
    """Regression coverage: rules 2-4 (too short / embedding failure /
    threshold cutoff) must behave exactly as before this change."""

    def test_clip_too_short_is_onzeker_without_calling_embedding(self):
        turn = make_turn(0, 0.0, 0.5, overlap=False, uncertain_assignment=False)  # 0.5s < default 1.0s
        recognizer = FakeRecognizer(similarity=0.9)
        [result] = assign_docent_roles([turn], DUMMY_WAVEFORM, SAMPLE_RATE, recognizer, make_config())

        self.assertEqual(result.docent_role, ROLE_ONZEKER)
        self.assertEqual(recognizer.call_count, 0)

    def test_embedding_failure_is_onzeker(self):
        turn = make_turn(0, 0.0, 5.0, overlap=False, uncertain_assignment=False)
        recognizer = FakeRecognizer(similarity=None, warning="empty clip")
        [result] = assign_docent_roles([turn], DUMMY_WAVEFORM, SAMPLE_RATE, recognizer, make_config())

        self.assertEqual(result.docent_role, ROLE_ONZEKER)
        self.assertIn("embedding mislukt", result.docent_role_note)

    def test_threshold_is_configurable_and_unchanged_default(self):
        cfg = make_config()
        self.assertEqual(cfg.similarity_threshold, 0.35)


class TestExistingMetadataPreserved(unittest.TestCase):
    """docent_role_threshold / docent_role_reference_audio must still be
    filled in on every path, regardless of which rule fired."""

    def test_metadata_present_on_docent_result(self):
        turn = make_turn(0, 0.0, 5.0, overlap=True)
        recognizer = FakeRecognizer(similarity=0.8)
        cfg = make_config(threshold=0.35)
        [result] = assign_docent_roles([turn], DUMMY_WAVEFORM, SAMPLE_RATE, recognizer, cfg)

        self.assertEqual(result.docent_role_threshold, 0.35)
        self.assertEqual(result.docent_role_reference_audio, "fictief_docent_ref.mp3")

    def test_metadata_present_on_onzeker_result(self):
        turn = make_turn(0, 0.0, 5.0, uncertain_assignment=True)
        recognizer = FakeRecognizer(similarity=0.8)
        cfg = make_config(threshold=0.35)
        [result] = assign_docent_roles([turn], DUMMY_WAVEFORM, SAMPLE_RATE, recognizer, cfg)

        self.assertEqual(result.docent_role_threshold, 0.35)
        self.assertEqual(result.docent_role_reference_audio, "fictief_docent_ref.mp3")

    def test_never_reorders_or_drops_turns(self):
        turns = [make_turn(i, i * 2.0, i * 2.0 + 2.0) for i in range(4)]
        recognizer = FakeRecognizer(similarity=0.5)
        results = assign_docent_roles(turns, DUMMY_WAVEFORM, SAMPLE_RATE, recognizer, make_config())
        self.assertEqual([t.turn_id for t in results], [0, 1, 2, 3])

    def test_input_turns_not_mutated(self):
        turn = make_turn(0, 0.0, 5.0)
        recognizer = FakeRecognizer(similarity=0.8)
        assign_docent_roles([turn], DUMMY_WAVEFORM, SAMPLE_RATE, recognizer, make_config())
        self.assertIsNone(turn.docent_role)  # the original object must stay untouched


if __name__ == "__main__":
    unittest.main()
