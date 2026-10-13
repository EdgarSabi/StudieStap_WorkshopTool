"""Test alleen de MECHANIEK van score_run.py (bestanden vinden, alle onderdelen scoren, één nieuw bestand schrijven, niet overschrijven).

De invoer is een tijdelijke nagebouwde rundirectory op basis van oude cachebestanden. Dat is uitdrukkelijk GEEN baseline en de
getallen worden niet gebruikt; er wordt alleen gecontroleerd dat de structuur klopt en dat circulariteit wordt herkend."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from helpers import HERE                                                     # noqa: F401
from baseline_eval import diar as D                                           # noqa: E402
from baseline_eval import refs as R                                           # noqa: E402
from baseline_eval import settings as S                                       # noqa: E402

CACHE = S.REPO / "Data-local" / "processed"


def build_fixture_run(td: Path, frag: str) -> Path:
    spec = S.FRAGMENTS[frag]
    ref = R.load_reference(S.GT_DIR / spec["ref"], frag)
    d = td / frag
    (d / "01_transcript").mkdir(parents=True)
    (d / "02_diarization").mkdir()
    (d / "04_docent").mkdir()
    shutil.copy(CACHE / f"{frag}.json", d / "01_transcript" / f"{frag}.json")
    shutil.copy(CACHE / "diarization" / f"{frag}_diarized.json", d / "02_diarization" / f"{frag}_diarized.json")
    dz = json.loads((d / "02_diarization" / f"{frag}_diarized.json").read_text(encoding="utf-8"))
    D.write_rttm([{"start": s["start"], "end": s["end"], "speaker": s["speaker_raw"]} for s in dz["segments"] if s.get("speaker_raw")],
                 frag, d / "02_diarization" / "raw_turns.rttm")
    rp = CACHE / "docent_recognition" / f"{frag}_diarized_turns_docent_roles.json"
    if rp.exists():
        shutil.copy(rp, d / "04_docent" / f"{frag}_diarized_turns_docent_roles.json")
    dur = json.loads((d / "01_transcript" / f"{frag}.json").read_text(encoding="utf-8"))["duration"]
    (d / "run_manifest.json").write_text(json.dumps({"fragment": frag, "inputs": {"audio_duration_s": dur,
                                                      "reference_sha256": ref.sha256}}), encoding="utf-8")
    return d


@unittest.skipUnless((CACHE / "testaudio2_fragment.json").exists(), "cachefixture ontbreekt")
class ScoreRunMechanics(unittest.TestCase):
    def run_score(self, d: Path, tag="scores_v1"):
        return subprocess.run([sys.executable, "-B", str(S.REPO / "Data-analysis" / "Experiments" / "baseline_evaluation" / "score_run.py"),
                               "--run-dir", str(d), "--tag", tag], capture_output=True, text=True)

    def test_scores_all_parts_and_refuses_to_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            d = build_fixture_run(Path(td), "testaudio2_fragment")
            r = self.run_score(d)
            self.assertEqual(r.returncode, 0, r.stderr[-800:])
            out = json.loads((d / "scores_v1.json").read_text(encoding="utf-8"))
            for k in ("text", "evidence", "der_raw_turns", "der_segment_level_hypothesis", "segment_eval", "docent_roles", "circularity"):
                self.assertIn(k, out)
            self.assertEqual(len(out["der_raw_turns"]), 8)                      # 2 uem x 2 overlap x 2 collar, vooraf vastgelegd
            self.assertEqual(out["quality_warning_unintelligible"]["used_for_exclusion"], False)
            self.assertEqual(out["docent_roles"]["status"], "ok")
            before = (d / "scores_v1.json").read_text(encoding="utf-8")
            again = self.run_score(d)                                            # tweede keer zelfde tag: moet falen
            self.assertNotEqual(again.returncode, 0)
            self.assertEqual((d / "scores_v1.json").read_text(encoding="utf-8"), before)

    def test_circular_reference_is_flagged_for_testaudio4_and_not_for_raster(self):
        if not (CACHE / "testaudio4_fragment.json").exists():
            self.skipTest("testaudio4 cache ontbreekt")
        with tempfile.TemporaryDirectory() as td:
            d4 = build_fixture_run(Path(td), "testaudio4_fragment")
            d2 = build_fixture_run(Path(td), "testaudio2_fragment")
            self.assertEqual(self.run_score(d4).returncode, 0)
            self.assertEqual(self.run_score(d2).returncode, 0)
            s4 = json.loads((d4 / "scores_v1.json").read_text(encoding="utf-8"))
            s2 = json.loads((d2 / "scores_v1.json").read_text(encoding="utf-8"))
            self.assertTrue(s4["circularity"]["circular"])                       # voorspelling: 87/87 identiek aan Whisper
            self.assertEqual(s4["evidence"]["wer_cer"], "not_reportable_circular")
            self.assertEqual(s4["text"]["status"], "circular_reference_do_not_report")
            self.assertFalse(s2["circularity"]["circular"])                      # voorspelling: raster wijkt af (16/19)
            self.assertEqual(s2["evidence"]["wer_cer"], "exploratory")

    def test_changed_reference_hash_blocks_scoring(self):
        with tempfile.TemporaryDirectory() as td:
            d = build_fixture_run(Path(td), "testaudio2_fragment")
            m = json.loads((d / "run_manifest.json").read_text(encoding="utf-8"))
            m["inputs"]["reference_sha256"] = "0" * 64
            (d / "run_manifest.json").write_text(json.dumps(m), encoding="utf-8")
            r = self.run_score(d)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("hash verschilt", r.stderr + r.stdout)
            self.assertFalse((d / "scores_v1.json").exists())


if __name__ == "__main__":
    unittest.main()
