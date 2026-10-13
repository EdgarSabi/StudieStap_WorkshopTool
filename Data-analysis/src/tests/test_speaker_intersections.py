"""
Regressietests voor de verliesloze uitbreiding van de sprekerkoppeling (assign_speakers + preprocessing).

VERWACHTE UITKOMSTEN, VASTGELEGD VOOR UITVOERING (afgeleid uit tijdsrekenkunde, niet uit de implementatie):

T1  Exclusieve wissel A 0-4 | B 4-6 | A 6-10 en één ASR-segment 2,5-7 s.
    Intersections (gesorteerd op begin): A 2,5-4,0 (1,5 s), B 4,0-6,0 (2,0 s), A 6,0-7,0 (1,0 s).
    Dominant label blijft A (A 2,5 s > B 2,0 s) - ongewijzigd. multiple_raw_speakers = True. Tekst ongewijzigd.
    Na preprocessing: turn.raw_speaker_seconds == {A: 2,5, B: 2,0}, multiple_raw_speakers = True, en
    source_segments[0] bevat alle 3 intersections.
T2  Echte overlap: A 0-10 en B 4-6, segment 4-6. Intersections A 4-6 en B 4-6 (elk 2,0 s), multiple = True,
    en de intersectielijst is IDENTIEK voor beide invoervolgordes. (Het dominante label bij deze exacte gelijkstand
    is bestaand gedrag en hangt van de volgorde af; dat blijft zo en wordt hier alleen vastgelegd.)
T3  Bewaarde runs 1 en 2 (geen modelrun): herberekening met de nieuwe koppeling geeft voor alle 19 segmenten exact
    dezelfde speaker/speaker_raw/confidence/overlap/uncertain als de bewaarde uitvoer; SPEAKER_01 staat in precies 7 segmenten
    (1, 4, 5, 11, 12, 15, 16) en samen 3,898125 s (= totaal ruwe SPEAKER_01 binnen de segmenten); preprocessing geeft nog
    dezelfde 10 turns met dezelfde grenzen; SPEAKER_01 blijft zichtbaar in turn.raw_speaker_seconds.
T4  Normaal segment: één spreker A 0-10, segment 1-3 -> 1 intersection (1-3), multiple = False. Raken beurten het segment
    alleen op de rand (A 0-4, B 4-6, segment 0-4) -> alleen A, multiple = False. Geen overlappende beurt -> lege lijst,
    speaker None, multiple = False.
T5  Bewust foute representaties die een spreker weglaten (alleen dominante intersection; of alleen dominante in turn-samenvatting)
    MOETEN door dezelfde controles worden afgekeurd.
"""
import json
import unittest
from pathlib import Path

from config import PreprocessingConfig
from models import (RawSpeakerIntersection, TranscriptSegment, WorkshopTranscript)
from diarization import SpeakerTurn as RawTurn, DiarizationResult, assign_speakers, build_label_map
from preprocessing import build_speaker_turns, attach_context

CFG = dict(overlap_min_ratio=0.15, uncertain_coverage_below=0.60, uncertain_margin_below=0.15)  # = DiarizationConfig-defaults
REPO = Path(__file__).resolve().parents[3]
RUNS = REPO / "Data-local" / "evaluation" / "baseline_v1" / "runs"


def couple(turns, segs, text="tekst blijft intact"):
    res = DiarizationResult(turns=[RawTurn(s, e, l) for s, e, l in turns], backend="x", model="x", settings={}, runtime_seconds=0)
    lm = build_label_map(res)
    return assign_speakers([TranscriptSegment(start=s, end=e, text=text) for s, e in segs], res.turns, lm["map"], **CFG)


def to_turns(segments):
    cfg = PreprocessingConfig()
    return attach_context(build_speaker_turns(segments, max_gap_within_turn_seconds=cfg.max_gap_within_turn_seconds),
                          large_context_gap_seconds=cfg.large_context_gap_seconds)


def ivs(seg):
    return [(x.speaker_raw, round(x.start, 6), round(x.end, 6), round(x.duration, 6)) for x in seg.raw_speaker_intersections]


# ---- de eisen als herbruikbare controles, zodat bewust foute varianten er ook tegen gehouden kunnen worden ----
def check_t1(tc: unittest.TestCase, assign):
    segs = assign([(0, 4, "A"), (4, 6, "B"), (6, 10, "A")], [(2.5, 7)])
    s = segs[0]
    tc.assertEqual(ivs(s), [("A", 2.5, 4.0, 1.5), ("B", 4.0, 6.0, 2.0), ("A", 6.0, 7.0, 1.0)])
    tc.assertEqual((s.speaker_raw, s.text), ("A", "tekst blijft intact"))     # dominant ongewijzigd, tekst intact
    tc.assertTrue(s.multiple_raw_speakers)
    t = to_turns(segs)
    tc.assertEqual(len(t), 1)
    tc.assertEqual(t[0].raw_speaker_seconds, {"A": 2.5, "B": 2.0})
    tc.assertTrue(t[0].multiple_raw_speakers)
    tc.assertEqual(ivs(t[0].source_segments[0]), ivs(s))
    # via JSON-rondreis (zoals tussen de pipelinestappen) blijft het bestaan
    back = TranscriptSegment.model_validate_json(s.model_dump_json())
    tc.assertEqual(ivs(back), ivs(s))


def check_t2(tc: unittest.TestCase, assign):
    one = assign([(0, 10, "A"), (4, 6, "B")], [(4, 6)])[0]
    two = assign([(4, 6, "B"), (0, 10, "A")], [(4, 6)])[0]
    want = [("A", 4.0, 6.0, 2.0), ("B", 4.0, 6.0, 2.0)]
    tc.assertEqual(ivs(one), want)
    tc.assertEqual(ivs(two), want)                      # onafhankelijk van de invoervolgorde
    tc.assertTrue(one.multiple_raw_speakers and two.multiple_raw_speakers)


class RegressionT1T2T4(unittest.TestCase):
    def test_T1_consecutive_speakers_inside_one_segment_survive_preprocessing(self):
        check_t1(self, couple)

    def test_T1_dominant_label_unchanged_legacy_values(self):
        s = couple([(0, 4, "A"), (4, 6, "B"), (6, 10, "A")], [(2.5, 7)])[0]
        # waarden van de oorspronkelijke koppelingsregel (zie baseline_cause_review B2): A, confidence 2,5/4,5, overlap, onzeker
        self.assertEqual((s.speaker, s.speaker_raw), ("MAIN_SPEAKER", "A"))
        self.assertAlmostEqual(s.speaker_confidence, 0.5556, places=4)
        self.assertTrue(s.overlap)
        self.assertTrue(s.uncertain_assignment)

    def test_T2_true_overlap_both_kept_in_either_input_order(self):
        check_t2(self, couple)

    def test_T2_dominant_tie_is_legacy_order_dependent_and_unchanged(self):
        a_first = couple([(0, 10, "A"), (4, 6, "B")], [(4, 6)])[0]
        b_first = couple([(4, 6, "B"), (0, 10, "A")], [(4, 6)])[0]
        self.assertEqual((a_first.speaker_raw, b_first.speaker_raw), ("A", "B"))   # bestaand gedrag, bewust niet gewijzigd

    def test_T4_normal_single_speaker_segment_is_not_multiple(self):
        s = couple([(0, 10, "A")], [(1, 3)])[0]
        self.assertEqual(ivs(s), [("A", 1.0, 3.0, 2.0)])
        self.assertFalse(s.multiple_raw_speakers)
        t = to_turns([s])[0]
        self.assertEqual(t.raw_speaker_seconds, {"A": 2.0})
        self.assertFalse(t.multiple_raw_speakers)

    def test_T4_touching_only_at_boundary_does_not_count(self):
        s = couple([(0, 4, "A"), (4, 6, "B")], [(0, 4)])[0]
        self.assertEqual(ivs(s), [("A", 0.0, 4.0, 4.0)])
        self.assertFalse(s.multiple_raw_speakers)

    def test_T4_no_overlapping_turn_gives_empty_and_not_multiple(self):
        s = couple([(0, 4, "A")], [(5, 6)])[0]
        self.assertEqual((s.speaker, s.raw_speaker_intersections, s.multiple_raw_speakers), (None, [], False))
        t = to_turns([s])[0]
        self.assertEqual((t.raw_speaker_seconds, t.multiple_raw_speakers), ({}, False))

    def test_same_label_two_turns_is_not_multiple_but_both_intervals_kept(self):
        s = couple([(0, 3, "A"), (3.5, 6, "A")], [(1, 5)])[0]
        self.assertEqual(ivs(s), [("A", 1.0, 3.0, 2.0), ("A", 3.5, 5.0, 1.5)])
        self.assertFalse(s.multiple_raw_speakers)

    def test_old_json_without_new_fields_still_loads_with_empty_defaults(self):
        old = {"start": 0.0, "end": 1.0, "text": "x", "speaker": "MAIN_SPEAKER", "speaker_raw": "SPEAKER_00"}
        seg = TranscriptSegment.model_validate(old)
        self.assertEqual((seg.raw_speaker_intersections, seg.multiple_raw_speakers), ([], False))


class FalsificationOfLossyRepresentations(unittest.TestCase):
    """Bewust foute representaties moeten door dezelfde controles worden afgekeurd."""

    @staticmethod
    def lossy_keep_only_dominant(turns, segs):
        out = couple(turns, segs)
        res = []
        for s in out:
            keep = [x for x in s.raw_speaker_intersections if x.speaker_raw == s.speaker_raw]
            res.append(s.model_copy(update={"raw_speaker_intersections": keep, "multiple_raw_speakers": False}))
        return res

    @staticmethod
    def order_dependent_drop_second(turns, segs):
        out = couple(turns, segs)
        return [s.model_copy(update={"raw_speaker_intersections": s.raw_speaker_intersections[:1]}) for s in out]

    def test_dominant_only_representation_fails_T1(self):
        with self.assertRaises(AssertionError):
            check_t1(self, self.lossy_keep_only_dominant)

    def test_dominant_only_representation_fails_T2(self):
        with self.assertRaises(AssertionError):
            check_t2(self, self.lossy_keep_only_dominant)

    def test_dropping_second_intersection_fails_T1_and_T2(self):
        with self.assertRaises(AssertionError):
            check_t1(self, self.order_dependent_drop_second)
        with self.assertRaises(AssertionError):
            check_t2(self, self.order_dependent_drop_second)

    def test_turn_summary_without_minority_speaker_fails_check(self):
        segs = couple([(0, 4, "A"), (4, 6, "B"), (6, 10, "A")], [(2.5, 7)])
        t = to_turns(segs)[0]
        lossy = t.model_copy(update={"raw_speaker_seconds": {"A": 2.5}})
        self.assertNotEqual(lossy.raw_speaker_seconds, {"A": 2.5, "B": 2.0})   # de echte uitvoer wijkt hier aantoonbaar van af
        self.assertEqual(t.raw_speaker_seconds, {"A": 2.5, "B": 2.0})


class RecouplingOfAnEnrichedSegment(unittest.TestCase):
    """Correctie na de onafhankelijke review: een eerder verrijkt segment dat opnieuw wordt gekoppeld mag geen oude
    intersections of meersprekersvlag behouden (model_copy bewaart niet-bijgewerkte velden).

    VERWACHT, VOOR UITVOERING:
      - eerste koppeling segment 0-2 met A 0-2 en B 0,5-1: A 2,0 s + B 0,5 s, multiple = True, dominant A;
      - opnieuw met LEGE turnlijst, met NIET-OVERLAPPENDE turn (C 5-6) en met ONGELDIGE duur (begin = eind):
        speaker/speaker_raw None, uncertain True, raw_speaker_intersections == [], multiple False;
      - preprocessing daarvan: raw_speaker_seconds == {} en multiple False; JSON-rondreis idem;
      - het invoersegment is daarna nog exact gelijk aan vóór de aanroep (geen mutatie): A 2,0 s, B 0,5 s;
      - opnieuw met geldige, andere turn (C 0-2) VERVANGT de lijst: alleen C 0-2, multiple False (geen A/B-restanten);
      - een variant die de oude velden laat staan (de oorspronkelijke fout) wordt door dezelfde controle afgekeurd.
    """

    @staticmethod
    def enriched():
        return couple([(0, 2, "A"), (0.5, 1, "B")], [(0, 2)])[0]

    @staticmethod
    def recouple(seg, turns):
        res = DiarizationResult(turns=[RawTurn(s, e, l) for s, e, l in turns], backend="x", model="x", settings={}, runtime_seconds=0)
        return assign_speakers([seg], res.turns, build_label_map(res)["map"], **CFG)[0]

    def check_cleared(self, recouple_fn, seg, turns, label):
        before = seg.model_dump()
        out = recouple_fn(seg, turns)
        self.assertIsNone(out.speaker, label)
        self.assertIsNone(out.speaker_raw, label)
        self.assertTrue(out.uncertain_assignment, label)
        self.assertEqual(out.raw_speaker_intersections, [], f"{label}: oude intersections bleven achter")
        self.assertFalse(out.multiple_raw_speakers, f"{label}: oude meersprekervlag bleef achter")
        # preprocessing
        t = to_turns([out])[0]
        self.assertEqual(t.raw_speaker_seconds, {}, label)
        self.assertFalse(t.multiple_raw_speakers, label)
        self.assertEqual(t.source_segments[0].raw_speaker_intersections, [], label)
        # JSON-rondreis van segment, transcript en verwerkt transcript
        back = TranscriptSegment.model_validate_json(out.model_dump_json())
        self.assertEqual((back.raw_speaker_intersections, back.multiple_raw_speakers), ([], False), label)
        wt = WorkshopTranscript(audio_file="x", language="nl", duration=2.0, segments=[out], model_size="m", transcription_time_seconds=0.0)
        wt2 = WorkshopTranscript.model_validate_json(wt.model_dump_json())
        self.assertEqual((wt2.segments[0].raw_speaker_intersections, wt2.segments[0].multiple_raw_speakers), ([], False), label)
        from models import ProcessedTranscript
        pt = ProcessedTranscript(source_transcript_path="x", audio_file="x", language="nl", duration=2.0, model_size="m",
                                 original_segment_count=1, turns=[t])
        pt2 = ProcessedTranscript.model_validate_json(pt.model_dump_json())
        self.assertEqual((pt2.turns[0].raw_speaker_seconds, pt2.turns[0].multiple_raw_speakers,
                          pt2.turns[0].source_segments[0].raw_speaker_intersections), ({}, False, []), label)
        # invoer niet gemuteerd
        self.assertEqual(seg.model_dump(), before, f"{label}: het invoersegment is gemuteerd")
        return out

    def test_precondition_first_coupling_has_both_speakers(self):
        s = self.enriched()
        self.assertEqual(ivs(s), [("A", 0.0, 2.0, 2.0), ("B", 0.5, 1.0, 0.5)])
        self.assertTrue(s.multiple_raw_speakers)
        self.assertEqual(s.speaker_raw, "A")
        self.assertEqual(to_turns([s])[0].raw_speaker_seconds, {"A": 2.0, "B": 0.5})

    def test_recoupling_with_empty_raw_input_clears_old_information(self):
        self.check_cleared(self.recouple, self.enriched(), [], "lege invoer")

    def test_recoupling_with_non_overlapping_raw_input_clears_old_information(self):
        self.check_cleared(self.recouple, self.enriched(), [(5, 6, "C")], "niet-overlappend")

    def test_recoupling_with_invalid_segment_duration_clears_old_information(self):
        stale = self.enriched().model_copy(update={"start": 2.0, "end": 2.0})   # duur 0, oude intersections nog aanwezig
        self.assertEqual(len(stale.raw_speaker_intersections), 2)
        self.check_cleared(self.recouple, stale, [(0, 4, "A"), (0.5, 1, "B")], "duur 0")
        reversed_ = self.enriched().model_copy(update={"start": 3.0, "end": 1.0})  # eind < begin
        self.check_cleared(self.recouple, reversed_, [(0, 4, "A")], "eind < begin")

    def test_input_segment_keeps_its_original_information_after_recoupling(self):
        s = self.enriched()
        self.recouple(s, [])
        self.assertEqual(ivs(s), [("A", 0.0, 2.0, 2.0), ("B", 0.5, 1.0, 0.5)])   # A 2,0 s en B 0,5 s nog aanwezig
        self.assertTrue(s.multiple_raw_speakers)
        self.assertEqual(to_turns([s])[0].raw_speaker_seconds, {"A": 2.0, "B": 0.5})

    def test_recoupling_with_valid_new_input_replaces_instead_of_appending(self):
        out = self.recouple(self.enriched(), [(0, 2, "C")])
        self.assertEqual(ivs(out), [("C", 0.0, 2.0, 2.0)])
        self.assertFalse(out.multiple_raw_speakers)
        self.assertEqual(to_turns([out])[0].raw_speaker_seconds, {"C": 2.0})

    def test_variant_that_keeps_stale_fields_is_rejected_by_the_same_check(self):
        def stale_keeping(seg, turns):          # de oorspronkelijke fout: de oude velden terugzetten
            out = self.recouple(seg, turns)
            return out.model_copy(update={"raw_speaker_intersections": list(seg.raw_speaker_intersections),
                                          "multiple_raw_speakers": seg.multiple_raw_speakers})
        for turns in ([], [(5, 6, "C")]):
            with self.assertRaises(AssertionError):
                self.check_cleared(stale_keeping, self.enriched(), turns, "foute variant")


@unittest.skipUnless((RUNS / "20261012_dev_run1" / "testaudio2_fragment" / "02_diarization" / "raw_turns.json").exists(),
                     "bewaarde baselineruns ontbreken")
class RegressionT3StoredBaselineRuns(unittest.TestCase):
    EXPECTED_SEGMENTS_WITH_SPEAKER_01 = [1, 4, 5, 11, 12, 15, 16]

    def replay(self, run_id):
        d = RUNS / run_id / "testaudio2_fragment"
        raw = json.loads((d / "02_diarization" / "raw_turns.json").read_text(encoding="utf-8"))["turns"]
        tr = WorkshopTranscript.model_validate_json(next((d / "01_transcript").glob("*.json")).read_text(encoding="utf-8"))
        saved = json.loads(next((d / "02_diarization").glob("*_diarized.json")).read_text(encoding="utf-8"))
        saved_pre = json.loads(next((d / "03_preprocessing").glob("*.json")).read_text(encoding="utf-8"))
        res = DiarizationResult(turns=[RawTurn(t["start"], t["end"], t["speaker"]) for t in raw], backend="x", model="x", settings={}, runtime_seconds=0)
        lm = build_label_map(res)
        new = assign_speakers(tr.segments, res.turns, lm["map"], **CFG)
        return raw, new, saved, saved_pre

    def test_T3_dominant_labels_unchanged_and_speaker_01_visible(self):
        for run_id in ("20261012_dev_run1", "20261012_dev_run2"):
            raw, new, saved, saved_pre = self.replay(run_id)
            # (1) alles wat al bestond is gelijk aan de bewaarde uitvoer
            for i, (n, o) in enumerate(zip(new, saved["segments"])):
                for f in ("speaker", "speaker_raw", "speaker_confidence", "overlap", "uncertain_assignment", "start", "end", "text"):
                    self.assertEqual(getattr(n, f), o[f], f"{run_id} segment {i} veld {f}")
            self.assertEqual({n.speaker_raw for n in new}, {"SPEAKER_00"})          # dominant: nog steeds alleen SPEAKER_00
            # (2) SPEAKER_01 zichtbaar in precies de verwachte 7 segmenten
            with_01 = [i for i, n in enumerate(new) if any(x.speaker_raw == "SPEAKER_01" for x in n.raw_speaker_intersections)]
            self.assertEqual(with_01, self.EXPECTED_SEGMENTS_WITH_SPEAKER_01, run_id)
            self.assertTrue(all(new[i].multiple_raw_speakers for i in with_01))
            self.assertEqual(sum(n.multiple_raw_speakers for n in new), 7)
            # (3) onafhankelijk oordeel: seconden per ruwe spreker met een raster van 1 ms
            segs = [(n.start, n.end) for n in new]
            for label in ("SPEAKER_00", "SPEAKER_01"):
                turns = [(t["start"], t["end"]) for t in raw if t["speaker"] == label]
                grid = sum(1 for k in range(int(segs[-1][1] * 1000)) if any(a <= (k + .5) / 1000 < b for a, b in segs)
                           and any(a <= (k + .5) / 1000 < b for a, b in turns))
                got = sum(x.duration for n in new for x in n.raw_speaker_intersections if x.speaker_raw == label)
                self.assertAlmostEqual(got, grid / 1000, delta=0.005, msg=f"{run_id} {label}")
            self.assertAlmostEqual(sum(x.duration for n in new for x in n.raw_speaker_intersections if x.speaker_raw == "SPEAKER_01"), 3.898125, places=5)
            # (4) preprocessing: zelfde turngroepering als de bewaarde run, SPEAKER_01 nog zichtbaar
            turns = to_turns(new)
            self.assertEqual([(t.start, t.end, t.speaker, t.overlap, t.uncertain_assignment) for t in turns],
                             [(t["start"], t["end"], t["speaker"], t["overlap"], t["uncertain_assignment"]) for t in saved_pre["turns"]])
            self.assertAlmostEqual(sum(t.raw_speaker_seconds.get("SPEAKER_01", 0.0) for t in turns), 3.898125, places=5)
            self.assertEqual(len(turns), 10)

    def test_T3_control_C_aligned_boundaries_stay_A_B_A_without_false_multiple(self):
        out = couple([(0, 4, "A"), (4, 6, "B"), (6, 10, "A")], [(0, 4), (4, 6), (6, 10)])
        self.assertEqual([s.speaker_raw for s in out], ["A", "B", "A"])
        self.assertEqual([s.multiple_raw_speakers for s in out], [False, False, False])

    def test_T3_a_representation_without_speaker_01_would_be_rejected(self):
        _, new, _, _ = self.replay("20261012_dev_run1")
        stripped = [n.model_copy(update={"raw_speaker_intersections": [x for x in n.raw_speaker_intersections if x.speaker_raw != "SPEAKER_01"]}) for n in new]
        with_01 = [i for i, n in enumerate(stripped) if any(x.speaker_raw == "SPEAKER_01" for x in n.raw_speaker_intersections)]
        self.assertNotEqual(with_01, self.EXPECTED_SEGMENTS_WITH_SPEAKER_01)   # de controle uit de echte test zou hier falen


if __name__ == "__main__":
    unittest.main()
