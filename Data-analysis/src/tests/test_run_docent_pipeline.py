"""
Test for the --force bug fix in run_docent_pipeline.py: preprocessing.py has
no --force flag (it always overwrites unconditionally), so the wrapper must
NOT pass --force to that one step, while still passing it to the three
steps that do support it.

Runs main() with subprocess.run() mocked out (returns success immediately,
no real transcription/diarization/etc. happens) so this test is fast and
doesn't need real audio or a HuggingFace token — it only checks WHICH
arguments each step is called with.
"""
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import run_docent_pipeline


def _fake_completed_process(*args, **kwargs):
    return SimpleNamespace(returncode=0)


class TestForceFlagPerStep(unittest.TestCase):
    def _run_with_argv(self, argv):
        calls = []

        def record_and_succeed(popen_args, **kwargs):
            calls.append(popen_args)
            return _fake_completed_process()

        with patch.object(run_docent_pipeline.subprocess, "run", side_effect=record_and_succeed), \
             patch.object(sys, "argv", ["run_docent_pipeline.py", *argv]):
            run_docent_pipeline.main()
        return calls

    def test_force_flag_reaches_transcription_diarization_and_docent_recognition(self):
        calls = self._run_with_argv(["testaudio1_fragment.mp3", "--force"])
        self.assertEqual(len(calls), 4)
        transcription_call, diarization_call, preprocessing_call, docent_call = calls

        self.assertIn("--force", transcription_call)
        self.assertIn("--force", diarization_call)
        self.assertIn("--force", docent_call)

    def test_force_flag_does_not_reach_preprocessing(self):
        """The actual bug: preprocessing.py doesn't accept --force, so the
        wrapper must never pass it there, even when --force was given."""
        calls = self._run_with_argv(["testaudio1_fragment.mp3", "--force"])
        preprocessing_call = calls[2]
        self.assertIn("preprocessing.py", preprocessing_call)
        self.assertNotIn("--force", preprocessing_call)

    def test_without_force_flag_nothing_gets_force(self):
        calls = self._run_with_argv(["testaudio1_fragment.mp3"])
        for call in calls:
            self.assertNotIn("--force", call)

    def test_all_four_steps_still_run_in_order(self):
        calls = self._run_with_argv(["testaudio1_fragment.mp3", "--force"])
        script_names = [call[1] for call in calls]  # [sys.executable, script.py, ...]
        self.assertEqual(script_names, [
            "transcription.py", "diarization.py", "preprocessing.py", "docent_recognition.py",
        ])


class TestRefinementOptionsReachDiarization(unittest.TestCase):
    def _diar_call(self, argv):
        calls = []
        with patch.object(run_docent_pipeline.subprocess, "run",
                          side_effect=lambda a, **k: calls.append(a) or _fake_completed_process()), \
             patch.object(sys, "argv", ["run_docent_pipeline.py", *argv]):
            run_docent_pipeline.main()
        return calls[1], calls

    def test_defaults_add_nothing(self):
        diar, _ = self._diar_call(["testaudio1_fragment.mp3"])
        self.assertNotIn("--no-refine", diar)
        self.assertNotIn("--min-cluster-size", diar)

    def test_options_only_go_to_diarization(self):
        diar, calls = self._diar_call(["testaudio1_fragment.mp3", "--no-refine", "--min-cluster-size", "8"])
        self.assertIn("--no-refine", diar)
        self.assertEqual(diar[diar.index("--min-cluster-size") + 1], "8")
        for other in (calls[0], calls[2], calls[3]):
            self.assertNotIn("--no-refine", other)
            self.assertNotIn("--min-cluster-size", other)


if __name__ == "__main__":
    unittest.main()
