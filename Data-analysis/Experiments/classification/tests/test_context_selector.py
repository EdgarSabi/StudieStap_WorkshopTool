"""STAP 7 tests: context windows (A/B/C) select the right turns, the center
turn stays identifiable, and no turn is ever counted twice as a center."""
import unittest

from tests import FIXTURES_DIR
from loaders import load_manual_fixture, load_pipeline_processed
from context.selector import select_context, iter_context_windows

MANUAL_PATH = FIXTURES_DIR / "tiny_manual.json"
PIPELINE_PATH = FIXTURES_DIR / "tiny_pipeline.json"


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
    def setUp(self):
        self.turns = load_manual_fixture(MANUAL_PATH).turns

    def test_one_window_per_turn_no_duplicates(self):
        for mode in ("A", "B", "C"):
            windows = list(iter_context_windows(self.turns, mode))
            self.assertEqual(len(windows), len(self.turns))
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
        window = select_context(turns, center_index=1, mode="A")  # just turn_id 1
        self.assertFalse(window.unknown_reliability)
        self.assertTrue(window.flagged_uncertain)

    def test_pipeline_clean_turn_is_known_and_not_flagged(self):
        turns = load_pipeline_processed(PIPELINE_PATH).turns  # turn 0: overlap=False, uncertain_assignment=False
        window = select_context(turns, center_index=0, mode="A")
        self.assertFalse(window.unknown_reliability)
        self.assertFalse(window.flagged_uncertain)


if __name__ == "__main__":
    unittest.main()
