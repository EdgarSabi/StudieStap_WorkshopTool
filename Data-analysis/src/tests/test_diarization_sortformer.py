"""
Tests voor de Sortformer-backend in diarization.py.

NeMo wordt hier vervangen door een nepmodule, zodat de test snel is en geen
NeMo-installatie of modeldownload nodig heeft. Gecontroleerd wordt alleen de
koppeling: NeMo-uitvoer -> SpeakerTurns -> de bestaande assign_speakers().
"""
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import diarization
from config import DiarizationConfig, SORTFORMER_POSTPROCESSING_PRESETS
from models import TranscriptSegment


class TestParseSortformerLines(unittest.TestCase):
    def test_lines_become_speaker_turns_with_pyannote_style_ids(self):
        turns = diarization.parse_sortformer_lines([
            "3.510 7.260 speaker_1",
            "0.500 3.120 speaker_0",
            "2.000 2.400 speaker_2",
        ])
        self.assertEqual([t.speaker for t in turns], ["SPEAKER_00", "SPEAKER_02", "SPEAKER_01"])
        self.assertAlmostEqual(turns[0].start, 0.5)
        self.assertAlmostEqual(turns[2].end, 7.26)

    def test_empty_and_zero_length_lines_are_skipped(self):
        turns = diarization.parse_sortformer_lines(["", "1.0 1.0 speaker_0", "garbage"])
        self.assertEqual(turns, [])

    def test_overlapping_speakers_flow_into_assign_speakers(self):
        """Sortformer geeft overlap als twee sprekers tegelijk actief; de
        bestaande assign_speakers() moet dat als overlap markeren."""
        turns = diarization.parse_sortformer_lines([
            "0.000 4.000 speaker_0",
            "2.500 4.000 speaker_1",   # korte tussenkomst over de docent heen
        ])
        seg = TranscriptSegment.model_construct(start=0.0, end=4.0, text="x")
        out = diarization.assign_speakers([seg], turns, {"SPEAKER_00": "MAIN_SPEAKER"})
        self.assertEqual(out[0].speaker, "MAIN_SPEAKER")
        self.assertTrue(out[0].overlap)


class _FakeModules:
    chunk_len = 0
    chunk_right_context = 0
    fifo_len = 0
    spkcache_update_period = 0
    spkcache_len = 0


class _FakeModel:
    last_call = None

    def __init__(self):
        self.sortformer_modules = _FakeModules()

    @classmethod
    def from_pretrained(cls, name, map_location=None):
        inst = cls()
        inst.loaded_name = name
        return inst

    def eval(self):
        return self

    def diarize(self, audio, batch_size, postprocessing_yaml=None, verbose=True):
        yaml_text = Path(postprocessing_yaml).read_text() if postprocessing_yaml else None
        _FakeModel.last_call = {"audio": audio, "yaml": yaml_text}
        return [["0.000 2.000 speaker_0", "2.000 2.600 speaker_1"]]


def _fake_nemo_modules():
    fake_torch = types.ModuleType("torch")
    fake_torch.device = lambda name: name
    models_mod = types.ModuleType("nemo.collections.asr.models")
    models_mod.SortformerEncLabelModel = _FakeModel
    return {
        "torch": sys.modules.get("torch", fake_torch),
        "nemo": types.ModuleType("nemo"),
        "nemo.collections": types.ModuleType("nemo.collections"),
        "nemo.collections.asr": types.ModuleType("nemo.collections.asr"),
        "nemo.collections.asr.models": models_mod,
    }


class TestSortformerBackend(unittest.TestCase):
    def test_get_backend_picks_sortformer_and_applies_streaming_settings(self):
        with patch.dict(sys.modules, _fake_nemo_modules()):
            backend = diarization.get_backend(DiarizationConfig(backend="sortformer"))
        self.assertIsInstance(backend, diarization.SortformerBackend)
        self.assertEqual(backend._model.loaded_name, "nvidia/diar_streaming_sortformer_4spk-v2.1")
        self.assertEqual(backend._model.sortformer_modules.chunk_len, 340)
        self.assertEqual(backend._model.sortformer_modules.spkcache_len, 188)

    def test_diarize_returns_turns_and_writes_postprocessing_yaml(self):
        config = DiarizationConfig(
            backend="sortformer",
            sortformer_postprocessing=SORTFORMER_POSTPROCESSING_PRESETS["dihard3"],
        )
        with patch.dict(sys.modules, _fake_nemo_modules()):
            backend = diarization.get_backend(config)
            result = backend.diarize(Path("x.wav"), max_speakers=6)
        self.assertEqual(result.backend, "sortformer")
        self.assertEqual(result.raw_speakers, ["SPEAKER_00", "SPEAKER_01"])
        self.assertIn("onset: 0.56", _FakeModel.last_call["yaml"])
        self.assertTrue(_FakeModel.last_call["yaml"].startswith("parameters:"))

    def test_default_postprocessing_passes_no_yaml(self):
        with patch.dict(sys.modules, _fake_nemo_modules()):
            backend = diarization.get_backend(DiarizationConfig(backend="sortformer"))
            backend.diarize(Path("x.wav"))
        self.assertIsNone(_FakeModel.last_call["yaml"])

    def test_unknown_backend_raises(self):
        with self.assertRaises(ValueError):
            diarization.get_backend(DiarizationConfig(backend="bestaat-niet"))


if __name__ == "__main__":
    unittest.main()
