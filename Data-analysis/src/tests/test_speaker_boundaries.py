"""
Tests voor speaker_boundaries.py (stap 2b) en de turn_confidence-regel in
diarization.assign_speakers().

Geen echt model, geen HF_TOKEN, geen audiobestanden: de "audio" is een
sinustoon per spreker (A = 200 Hz, B = 300 Hz, C = 450 Hz) en de
FakeEmbedder zet de dominante frequentie om in een vaste stem-vector plus
wat deterministische ruis. Zo is precies bekend wie waar spreekt, en test je
alleen de beslislogica.
"""
import unittest

import numpy as np

from config import BoundaryRefinementConfig
from diarization import SpeakerTurn, assign_speakers
from models import TranscriptSegment
from speaker_boundaries import NEW_SPEAKER_PREFIX, refine_speaker_boundaries

SR = 16000
FREQ = {"A": 200.0, "B": 300.0, "C": 450.0}
DIM = 16


def _voice_vectors():
    rng = np.random.default_rng(0)
    shared = rng.normal(size=DIM)
    vecs = {}
    for i, spk in enumerate(FREQ):
        v = np.zeros(DIM)
        v[i] = 3.0
        vecs[spk] = v + 0.3 * shared
    return vecs


VOICES = _voice_vectors()


class FakeEmbedder:
    """Dominante frequentie -> stem-vector + ruis. De ruis komt uit één vaste
    random-generator, dus elke run geeft exact dezelfde uitkomst."""

    def __init__(self, noise: float = 0.4):
        self.noise = noise
        self.calls = 0
        self._rng = np.random.default_rng(42)

    def embed(self, clips, sample_rate):
        self.calls += 1
        out = []
        for c in clips:
            c = np.asarray(c, dtype=np.float64)
            if len(c) < 0.3 * sample_rate or np.abs(c).max() < 1e-4:
                out.append(np.full(DIM, np.nan))
                continue
            spec = np.abs(np.fft.rfft(c))
            f = np.fft.rfftfreq(len(c), 1 / sample_rate)[int(np.argmax(spec))]
            spk = min(FREQ, key=lambda s: abs(FREQ[s] - f))
            noise = self._rng.normal(size=DIM)
            out.append(VOICES[spk] + self.noise * noise)
        return np.vstack(out)


def make_audio(script, total=None):
    """script: lijst (start, end, spreker). Stilte daartussen."""
    total = total or max(e for _, e, _ in script) + 0.5
    x = np.zeros(int(total * SR), dtype=np.float32)
    for s, e, spk in script:
        t = np.arange(int(s * SR), int(e * SR)) / SR
        x[int(s * SR):int(s * SR) + len(t)] = 0.3 * np.sin(2 * np.pi * FREQ[spk] * t)
    return x


# Een klasgesprek: A (docent) praat het meest, B (leerling) een paar keer kort,
# telkens met 0,2 s stilte ertussen.
SCRIPT = [
    (0.0, 3.0, "A"), (3.2, 4.6, "B"), (4.8, 8.0, "A"),
    (8.2, 9.6, "B"), (9.8, 13.0, "A"), (13.2, 14.6, "B"),
    (14.8, 18.0, "A"), (18.2, 19.6, "B"), (19.8, 23.0, "A"),
]
ASR = [(s, e) for s, e, _ in SCRIPT]


def turns_from(script, rename=None):
    rename = rename or {}
    return [SpeakerTurn(s, e, rename.get((s, e), f"SPK_{spk}")) for s, e, spk in script]


def label_at(turns, t):
    return {x.speaker for x in turns if x.start <= t < x.end}


class TestMissedSpeakerChange(unittest.TestCase):
    def test_b_turn_that_pyannote_gave_to_a_is_relabeled(self):
        """Het testaudio2-probleem: pyannote zet een beurt van B bij A, zonder
        overlap of onzekerheid. Met Whisper-grenzen moet die terug naar B."""
        audio = make_audio(SCRIPT)
        wrong = turns_from(SCRIPT, rename={(3.2, 4.6): "SPK_A"})
        res = refine_speaker_boundaries(audio, SR, wrong, FakeEmbedder(), BoundaryRefinementConfig(), asr_spans=ASR)
        self.assertEqual(label_at(res.turns, 3.9), {"SPK_B"})
        self.assertTrue(any(c["from"] == "SPK_A" and c["to"] == "SPK_B" for c in res.changes))
        # de rest blijft zoals het was
        self.assertEqual(label_at(res.turns, 1.0), {"SPK_A"})
        self.assertEqual(label_at(res.turns, 8.9), {"SPK_B"})

    def test_change_without_any_pyannote_boundary_is_found_via_whisper_boundary(self):
        """Pyannote ziet 0-8 s als één A-beurt (geen grens op 3,2 of 4,6 s).
        De Whisper-segmentgrenzen maken er aparte eenheden van."""
        audio = make_audio(SCRIPT)
        wrong = [SpeakerTurn(0.0, 8.0, "SPK_A")] + turns_from(SCRIPT[3:])
        res = refine_speaker_boundaries(audio, SR, wrong, FakeEmbedder(), BoundaryRefinementConfig(), asr_spans=ASR)
        self.assertEqual(label_at(res.turns, 3.9), {"SPK_B"})
        self.assertEqual(label_at(res.turns, 6.0), {"SPK_A"})


class TestDoesNotBreakCorrectInput(unittest.TestCase):
    def test_correct_diarization_is_left_alone(self):
        audio = make_audio(SCRIPT)
        good = turns_from(SCRIPT)
        res = refine_speaker_boundaries(audio, SR, good, FakeEmbedder(), BoundaryRefinementConfig(), asr_spans=ASR)
        relabels = [c for c in res.changes if not c.get("split")]
        self.assertEqual(relabels, [])
        self.assertEqual({k: v for k, v in res.merge_map.items() if k != v}, {})
        self.assertEqual(res.new_speakers, [])

    def test_short_unit_is_never_relabeled(self):
        """Stukjes korter dan min_relabel_seconds geven te ruisige embeddings
        om tegen pyannote in te gaan."""
        script = SCRIPT[:1] + [(3.2, 3.8, "B")] + SCRIPT[2:]
        audio = make_audio(script)
        wrong = turns_from(script, rename={(3.2, 3.8): "SPK_A"})
        res = refine_speaker_boundaries(audio, SR, wrong, FakeEmbedder(), BoundaryRefinementConfig(),
                                        asr_spans=[(s, e) for s, e, _ in script])
        self.assertEqual(label_at(res.turns, 3.5), {"SPK_A"})

    def test_no_turns_returns_input_unchanged(self):
        res = refine_speaker_boundaries(np.zeros(SR * 2, dtype=np.float32), SR, [], FakeEmbedder(),
                                        BoundaryRefinementConfig())
        self.assertEqual(res.turns, [])
        self.assertIn("skipped", res.stats)


class TestOverSegmentation(unittest.TestCase):
    def test_one_speaker_split_over_two_labels_is_merged(self):
        """Wat er gebeurt bij een lage min_cluster_size: docent A wordt in twee
        nep-sprekers gesplitst. Die moeten weer één spreker worden."""
        audio = make_audio(SCRIPT)
        split = turns_from(SCRIPT, rename={(14.8, 18.0): "SPK_A2", (19.8, 23.0): "SPK_A2", (9.8, 13.0): "SPK_A2"})
        res = refine_speaker_boundaries(audio, SR, split, FakeEmbedder(), BoundaryRefinementConfig(), asr_spans=ASR)
        merged = {k: v for k, v in res.merge_map.items() if k != v}
        self.assertEqual(len(merged), 1)
        self.assertIn(set(merged.items()).pop(), {("SPK_A2", "SPK_A"), ("SPK_A", "SPK_A2")})
        self.assertEqual(len({t.speaker for t in res.turns}), 2)  # A en B

    def test_two_real_speakers_are_not_merged(self):
        audio = make_audio(SCRIPT)
        res = refine_speaker_boundaries(audio, SR, turns_from(SCRIPT), FakeEmbedder(), BoundaryRefinementConfig(),
                                        asr_spans=ASR)
        self.assertEqual({t.speaker for t in res.turns}, {"SPK_A", "SPK_B"})


class TestNewSpeaker(unittest.TestCase):
    def test_third_speaker_hidden_inside_a_becomes_new_speaker(self):
        """Het testaudio4-probleem: een korte derde spreker (C) is door
        pyannote bij de docent gezet. C lijkt op niemand -> eigen spreker."""
        script = SCRIPT + [(23.2, 24.6, "C"), (24.8, 28.0, "A"), (28.2, 29.6, "C"), (29.8, 33.0, "A")]
        audio = make_audio(script)
        wrong = turns_from(script, rename={(23.2, 24.6): "SPK_A", (28.2, 29.6): "SPK_A"})
        res = refine_speaker_boundaries(audio, SR, wrong, FakeEmbedder(), BoundaryRefinementConfig(),
                                        asr_spans=[(s, e) for s, e, _ in script])
        self.assertEqual(len(res.new_speakers), 1)
        new = res.new_speakers[0]["label"]
        self.assertTrue(new.startswith(NEW_SPEAKER_PREFIX))
        self.assertEqual(label_at(res.turns, 23.9), {new})
        self.assertEqual(label_at(res.turns, 28.9), {new})
        # een nieuwe spreker is een onzekere vondst -> lage confidence
        conf = [t.confidence for t in res.turns if t.speaker == new]
        self.assertTrue(all(c == 0.0 for c in conf))

    def test_detection_can_be_switched_off(self):
        script = SCRIPT + [(23.2, 24.6, "C"), (24.8, 28.0, "A"), (28.2, 29.6, "C"), (29.8, 33.0, "A")]
        audio = make_audio(script)
        wrong = turns_from(script, rename={(23.2, 24.6): "SPK_A", (28.2, 29.6): "SPK_A"})
        cfg = BoundaryRefinementConfig(detect_new_speakers=False)
        res = refine_speaker_boundaries(audio, SR, wrong, FakeEmbedder(), cfg, asr_spans=[(s, e) for s, e, _ in script])
        self.assertEqual(res.new_speakers, [])


class TestTurnConfidenceInAssignSpeakers(unittest.TestCase):
    def _seg(self, s, e):
        return TranscriptSegment(start=s, end=e, text="x")

    def test_low_turn_confidence_marks_segment_uncertain(self):
        turns = [SpeakerTurn(0.0, 2.0, "S0", confidence=0.2), SpeakerTurn(2.0, 4.0, "S1", confidence=1.0)]
        out = assign_speakers([self._seg(0.1, 1.9), self._seg(2.1, 3.9)], turns, {"S0": "MAIN", "S1": "OTHER"},
                              turn_confidence_below=0.5)
        self.assertTrue(out[0].uncertain_assignment)
        self.assertFalse(out[1].uncertain_assignment)

    def test_without_threshold_behaviour_is_unchanged(self):
        """Zonder turn_confidence_below (of zonder refinement: confidence=None)
        werkt assign_speakers precies zoals vroeger."""
        turns = [SpeakerTurn(0.0, 2.0, "S0", confidence=0.0)]
        out = assign_speakers([self._seg(0.1, 1.9)], turns, {"S0": "MAIN"})
        self.assertFalse(out[0].uncertain_assignment)
        turns = [SpeakerTurn(0.0, 2.0, "S0")]
        out = assign_speakers([self._seg(0.1, 1.9)], turns, {"S0": "MAIN"}, turn_confidence_below=0.5)
        self.assertFalse(out[0].uncertain_assignment)


if __name__ == "__main__":
    unittest.main()
