"""Bewijs dat de runner de ORIGINELE modules aanroept en hun uitvoer écht omleidt, zónder een model te laden.

Gebruikt de originele preprocessing.main() (puur rekenwerk) met een bestaand diarized-bestand ALLEEN als invoerfixture.
Controleert dat er niets in Data-local/processed bijkomt en dat de bron-hashes ongewijzigd blijven."""
import sys
import tempfile
import unittest
from pathlib import Path

from helpers import HERE                                                    # noqa: F401  (zet sys.path, geen bytecode)
from baseline_eval import runlib as L                                        # noqa: E402
from baseline_eval import settings as S                                      # noqa: E402

FIXTURE = S.REPO / "Data-local" / "processed" / "diarization" / "testaudio2_fragment_diarized.json"


class Wiring(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(S.SRC))
        sys.dont_write_bytecode = True
        import config, transcription, diarization, preprocessing, docent_recognition   # noqa: E401
        cls.m = dict(config=config, transcription=transcription, diarization=diarization,
                     preprocessing=preprocessing, docent_recognition=docent_recognition)

    def test_all_patch_targets_exist_in_the_original_modules(self):
        m = self.m
        self.assertTrue(hasattr(m["transcription"], "PROCESSED_DATA_DIR"))
        self.assertTrue(hasattr(m["diarization"], "DIARIZATION_OUTPUT_DIR"))
        self.assertTrue(hasattr(m["diarization"].PyannoteBackend, "diarize"))
        self.assertTrue(hasattr(m["preprocessing"], "PREPROCESSING_OUTPUT_DIR"))
        self.assertTrue(hasattr(m["docent_recognition"], "DIARIZATION_OUTPUT_DIR"))
        self.assertTrue(hasattr(m["docent_recognition"], "DOCENT_RECOGNITION_OUTPUT_DIR"))

    def test_default_pipeline_settings_match_what_the_pipeline_script_uses(self):
        c = self.m["config"]
        t = c.TranscriptionConfig(model_size="medium")
        self.assertEqual((t.language, t.device, t.compute_type, t.beam_size, t.vad_filter, t.word_timestamps),
                         ("nl", "cpu", "int8", 5, True, False))
        d = c.DiarizationConfig()
        self.assertEqual((d.hf_model, d.min_speakers, d.max_speakers), ("pyannote/speaker-diarization-3.1", None, None))
        self.assertEqual(c.DocentRecognitionConfig(reference_audio="x").similarity_threshold, 0.35)

    @unittest.skipUnless(FIXTURE.exists(), "fixture ontbreekt")
    def test_preprocessing_is_redirected_and_nothing_else_is_touched(self):
        pre = self.m["preprocessing"]
        orig_dir = pre.PREPROCESSING_OUTPUT_DIR
        before = L.tree_snapshot(S.REPO / "Data-local" / "processed")
        src_before = {p.name: L.sha256(p) for p in S.SRC.glob("*.py")}
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "turns.json"
            r = L.run_original_main(pre, ["--diarized", FIXTURE, "--out", out], {"PREPROCESSING_OUTPUT_DIR": Path(td) / "pp"})
            self.assertEqual(r["status"], "ok", r["detail"])
            self.assertTrue(out.exists())
            self.assertTrue((Path(td) / "pp").is_dir())                       # de omgeleide map is gebruikt
            self.assertIn("segments -> turns", r["stdout"])
        self.assertEqual(pre.PREPROCESSING_OUTPUT_DIR, orig_dir)                  # hersteld
        self.assertEqual(L.diff_snapshots(before, L.tree_snapshot(S.REPO / "Data-local" / "processed")),
                         {"added": [], "removed": [], "changed": []})
        self.assertEqual(src_before, {p.name: L.sha256(p) for p in S.SRC.glob("*.py")})

    def test_missing_input_in_original_stage_is_reported_not_swallowed(self):
        pre = self.m["preprocessing"]
        with tempfile.TemporaryDirectory() as td:
            r = L.run_original_main(pre, ["--diarized", Path(td) / "bestaat_niet.json"], {"PREPROCESSING_OUTPUT_DIR": Path(td)})
        self.assertEqual(r["status"], "exit")
        self.assertIn("Not found", r["detail"])


if __name__ == "__main__":
    unittest.main()
