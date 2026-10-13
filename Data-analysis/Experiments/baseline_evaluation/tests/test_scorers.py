"""Onafhankelijke scorertests op kleine synthetische voorbeelden. De verwachte waarden zijn met de hand uit de tijdsrekenkunde
afgeleid (zie commentaar), NIET uit de te testen software. Draaien:

    Data-analysis/src/.venv/Scripts/python.exe -B -m unittest discover -s Data-analysis/Experiments/baseline_evaluation/tests -v
"""
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from helpers import make_ref, hyp, write_csv                                 # noqa: E402
from baseline_eval import text as T                                          # noqa: E402
from baseline_eval import refs as R                                          # noqa: E402
from baseline_eval import diar as D                                          # noqa: E402
from baseline_eval import runlib as L                                        # noqa: E402
from baseline_eval import settings as S                                      # noqa: E402


def der(ref, h, dur, uem="strict", overlap="keep", collar=0.0):
    return D.compute_der(R.speech_annotation(ref, dur), h, R.build_uem(ref, dur, uem, overlap), collar)


class TextChecks(unittest.TestCase):
    def test_1_perfect_transcript_wer_zero(self):
        r = T.wer("De kat zit op de mat", "de kat zit op de mat!")
        self.assertEqual((r["errors"], r["rate"]), (0, 0.0))

    def test_2_one_wrong_word(self):
        r = T.wer("de hond zit hier", "de kat zit hier")          # 1 van 4 woorden fout
        self.assertEqual((r["errors"], r["substitutions"], r["deletions"], r["insertions"]), (1, 1, 0, 0))
        self.assertAlmostEqual(r["rate"], 0.25)

    def test_deletion_and_insertion_counted_separately(self):
        d = T.wer("a b c d", "a c d")
        self.assertEqual((d["deletions"], d["insertions"], d["substitutions"]), (1, 0, 0))
        i = T.wer("a b c d", "a b x c d")
        self.assertEqual((i["insertions"], i["deletions"], i["substitutions"]), (1, 0, 0))

    def test_completely_wrong_hypothesis_is_one(self):
        self.assertAlmostEqual(T.wer("a b c d", "w x y z")["rate"], 1.0)

    def test_empty_reference_is_not_silently_zero(self):
        r = T.wer("", "iets")
        self.assertIsNone(r["rate"])
        self.assertIn("lege referentie", r["note"])

    def test_normalisation_rules(self):
        self.assertEqual(T.normalize("Eh... Heeft-ie z’n (moeilijk te volgen) HOND?"), "heeft ie z'n hond")
        self.assertEqual(T.normalize("uh, ja", remove_fillers=False), "uh ja")
        self.assertEqual(T.normalize("uh, ja"), "ja")                       # tussenwerpsel weg
        self.assertEqual(T.normalize("Oh nee, hè?"), "oh nee hè")           # lexicale tussenwerpsels blijven
        self.assertEqual(T.normalize("[applaus] ja"), "ja")

    def test_filler_variants_differ(self):
        self.assertEqual(T.wer("ja dat klopt", "ja uh dat klopt", True)["errors"], 0)
        self.assertEqual(T.wer("ja dat klopt", "ja uh dat klopt", False)["errors"], 1)

    def test_cer_known_value(self):
        self.assertAlmostEqual(T.cer("kat", "kot")["rate"], 1 / 3)

    def test_manual_txt_parsing_drops_labels_and_quotes(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "m.txt"
            p.write_text('Docent: "Zegt u het maar."\n\nLeerling 2: Ja, uh. (slecht te verstaan)\n', encoding="utf-8")
            self.assertEqual(T.normalize(R.manual_txt_text(p)), "zegt u het maar ja")


class DerChecks(unittest.TestCase):
    A_B = [dict(start=0, end=5, spk="A"), dict(start=5, end=10, spk="B")]

    def test_3_correct_intervals_der_zero_even_with_swapped_label_names(self):
        ref = make_ref(self.A_B)
        for h in (hyp((0, 5, "x"), (5, 10, "y")), hyp((0, 5, "y"), (5, 10, "x"))):
            r = der(ref, h, 10)
            self.assertEqual((r["der"], r["confusion_s"], r["missed_s"], r["false_alarm_s"]), (0.0, 0.0, 0.0, 0.0))

    def test_4a_confusion_two_speakers_merged_into_one(self):
        r = der(make_ref(self.A_B), hyp((0, 10, "x")), 10)       # B-spraak (5 s) krijgt het label van A
        self.assertAlmostEqual(r["confusion_s"], 5.0)
        self.assertEqual((r["missed_s"], r["false_alarm_s"]), (0.0, 0.0))
        self.assertAlmostEqual(r["der"], 0.5)

    def test_4b_missed_speech(self):
        r = der(make_ref(self.A_B), hyp((0, 5, "x")), 10)        # B ontbreekt geheel
        self.assertAlmostEqual(r["missed_s"], 5.0)
        self.assertEqual((r["confusion_s"], r["false_alarm_s"]), (0.0, 0.0))
        self.assertAlmostEqual(r["der"], 0.5)

    def test_4c_false_alarm_extra_activity_in_silence(self):
        ref = make_ref([dict(start=0, end=5, spk="A")])          # 5-10 s: stilte (niet gelabeld)
        r = der(ref, hyp((0, 10, "x")), 10, uem="strict")
        self.assertAlmostEqual(r["false_alarm_s"], 5.0)
        self.assertEqual((r["missed_s"], r["confusion_s"]), (0.0, 0.0))
        self.assertAlmostEqual(r["der"], 1.0)                    # 5 s fout / 5 s referentiespraak
        # in 'labelled' UEM wordt de stilte niet beoordeeld: false alarm is dan per definitie onzichtbaar
        self.assertEqual(der(ref, hyp((0, 10, "x")), 10, uem="labelled")["false_alarm_s"], 0.0)

    def test_collar_is_per_side(self):
        ref = make_ref([dict(start=0, end=10, spk="A")])
        h = hyp((0.2, 10, "x"))                                   # begin 0,2 s te laat
        self.assertAlmostEqual(der(ref, h, 10, collar=0.0)["missed_s"], 0.2)
        self.assertAlmostEqual(der(ref, h, 10, collar=0.25)["missed_s"], 0.0)   # 0,2 < 0,25 per kant
        self.assertGreater(der(ref, hyp((0.3, 10, "x")), 10, collar=0.25)["missed_s"], 0.0)  # 0,3 > 0,25: nog fout

    def test_5_simultaneous_speakers_are_kept(self):
        ref = make_ref([dict(start=0, end=10, spk="A"), dict(start=4, end=8, spk="B", overlap="ja")])
        ann = R.speech_annotation(ref, 10)
        self.assertEqual(sorted(ann.labels()), ["A", "B"])
        self.assertAlmostEqual(sum(s.duration for s in ann.get_overlap()), 4.0)
        one = der(ref, hyp((0, 10, "x")), 10)                      # totaal 14 s spraak; 4 s gemist
        self.assertAlmostEqual(one["total_ref_speech_s"], 14.0)
        self.assertAlmostEqual(one["missed_s"], 4.0)
        self.assertAlmostEqual(one["der"], 4 / 14)
        both = der(ref, hyp((0, 10, "x"), (4, 8, "y")), 10)
        self.assertEqual(both["der"], 0.0)
        # expliciete overlapbehandeling: 'exclude' haalt de 4 s gelijktijdige spraak uit de UEM
        ex = der(ref, hyp((0, 10, "x")), 10, overlap="exclude")
        self.assertAlmostEqual(ex["total_ref_speech_s"], 6.0)
        self.assertEqual(ex["der"], 0.0)

    def test_overlap_flag_rows_masked_in_exclude_mode(self):
        ref = make_ref([dict(start=0, end=5, spk="A"), dict(start=5, end=10, spk="B", overlap="ja")])
        r = der(ref, hyp((0, 10, "x")), 10, overlap="exclude")    # B-rij is gemarkeerd als overlap -> niet beoordeeld
        self.assertAlmostEqual(r["total_ref_speech_s"], 5.0)
        self.assertEqual(r["confusion_s"], 0.0)

    def test_6_unknown_speaker_is_not_a_new_person(self):
        ref = make_ref([dict(start=0, end=4, spk="A"), dict(start=4, end=6, spk="ONBEKEND", text="rumoer"),
                        dict(start=6, end=10, spk="A")])
        self.assertEqual(ref.speakers(), ["A"])
        self.assertEqual(sorted(R.speech_annotation(ref, 10).labels()), ["A"])
        h = hyp((0, 4, "x"), (4, 6, "y"), (6, 10, "x"))           # extra spreker alleen in het onbekende gebied
        r = der(ref, h, 10, uem="strict")
        self.assertEqual((r["false_alarm_s"], r["confusion_s"], r["missed_s"], r["der"]), (0.0, 0.0, 0.0, 0.0))
        # tegenvoorbeeld: hetzelfde gat ZONDER ONBEKEND-rij is stilte en geeft wél false alarm
        silent = make_ref([dict(start=0, end=4, spk="A"), dict(start=6, end=10, spk="A")])
        r2 = der(silent, h, 10, uem="strict")
        self.assertAlmostEqual(r2["false_alarm_s"], 2.0)
        self.assertAlmostEqual(r2["der"], 2 / 8)

    def test_nonspeech_and_cut_rows_are_masked_not_speakers(self):
        ref = make_ref([dict(start=0, end=4, spk="A"), dict(start=4, end=6, spk="GEEN", text="APPLAUS"),
                        dict(start=6, end=8, spk="A"), dict(start=8, end=10, spk="ONBEKEND", note="fragment knipt af, niet meenemen")])
        self.assertEqual(ref.speakers(), ["A"])
        self.assertEqual({r.kind for r in ref.rows}, {"speech", "nonspeech", "cut"})
        r = der(ref, hyp((0, 10, "x")), 10, uem="strict")
        self.assertEqual((r["false_alarm_s"], r["der"]), (0.0, 0.0))
        self.assertAlmostEqual(r["total_ref_speech_s"], 6.0)

    def test_reference_beyond_audio_is_clipped(self):
        ref = make_ref([dict(start=0, end=10.6, spk="A")])
        self.assertAlmostEqual(der(ref, hyp((0, 10, "x")), 10)["total_ref_speech_s"], 10.0)

    def test_empty_uem_is_explicit(self):
        ref = make_ref([dict(start=0, end=4, spk="GEEN")])
        self.assertEqual(D.der_grid(ref, hyp((0, 4, "x")), 4)["status"], "no_reference_speakers")

    def test_rttm_roundtrip_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.rttm"
            D.write_rttm([{"start": 0.0, "end": 1.5, "speaker": "SPEAKER_00"}, {"start": 1.0, "end": 2.0, "speaker": "SPEAKER_01"}], "u", p)
            a = D.read_rttm(p)
            self.assertEqual(sorted(a.labels()), ["SPEAKER_00", "SPEAKER_01"])
            self.assertAlmostEqual(sum(s.duration for s in a.get_overlap()), 0.5)   # gelijktijdige sprekers blijven behouden
            with self.assertRaises(FileExistsError):
                D.write_rttm([], "u", p)


class SegmentChecks(unittest.TestCase):
    def test_7_two_speakers_in_one_asr_segment_are_not_lost(self):
        ref = make_ref([dict(start=0, end=4, spk="A"), dict(start=4, end=5, spk="B")])
        self.assertEqual(ref.speakers(), ["A", "B"])                       # de referentie volgt NIET het ASR-segment
        seg = [{"start": 0.0, "end": 5.0, "speaker_raw": "SPEAKER_00"}]
        r = D.segment_eval(seg, ref, 5.0)
        self.assertEqual(r["segments"][0]["status"], "mixed")             # B beslaat 20% >= 15%
        self.assertEqual(r["status_counts"], {"mixed": 1})
        self.assertAlmostEqual(r["segments"][0]["ref_second_share"], 0.2)
        # en de ruwe DER met één label over het hele segment toont de fout als verwisseling van 1 s
        c = der(ref, hyp((0, 5, "x")), 5)
        self.assertAlmostEqual(c["confusion_s"], 1.0)
        self.assertAlmostEqual(c["der"], 0.2)

    def test_segment_matching_is_time_based_and_label_names_irrelevant(self):
        ref = make_ref([dict(start=0, end=4, spk="A"), dict(start=4, end=8, spk="B")])
        segs = [{"start": 4.0, "end": 8.0, "speaker_raw": "S0"}, {"start": 0.0, "end": 4.0, "speaker_raw": "S1"}]  # omgekeerde volgorde
        r = D.segment_eval(segs, ref, 8.0)
        self.assertAlmostEqual(r["single_accuracy_seconds"], 1.0)
        self.assertEqual(r["mapping_hyp_to_ref"], {"S1": "A", "S0": "B"})

    def test_wrong_hypothesis_scores_lower(self):
        ref = make_ref([dict(start=0, end=4, spk="A"), dict(start=4, end=8, spk="B")])
        segs = [{"start": 0.0, "end": 4.0, "speaker_raw": "Z"}, {"start": 4.0, "end": 8.0, "speaker_raw": "Z"}]
        self.assertAlmostEqual(D.segment_eval(segs, ref, 8.0)["single_accuracy_seconds"], 0.5)

    def test_unassigned_segment_counts_as_wrong_not_dropped(self):
        ref = make_ref([dict(start=0, end=4, spk="A")])
        r = D.segment_eval([{"start": 0.0, "end": 4.0, "speaker_raw": None}], ref, 4.0)
        self.assertEqual(r["status_counts"], {"single": 1})
        self.assertEqual(r["single_accuracy_seconds"], 0.0)

    def test_segment_in_unknown_region_is_masked_not_scored(self):
        ref = make_ref([dict(start=0, end=2, spk="A"), dict(start=2, end=6, spk="ONBEKEND")])
        r = D.segment_eval([{"start": 2.0, "end": 6.0, "speaker_raw": "S"}], ref, 6.0)
        self.assertEqual(r["status_counts"], {"masked": 1})

    def test_circularity_detector_flags_copied_text_and_not_independent_text(self):
        ref = make_ref([dict(start=0, end=2, spk="A", text="de kat zit"), dict(start=2, end=4, spk="B", text="op de mat")])
        same = [{"start": 0, "end": 2, "text": "De kat zit."}, {"start": 2, "end": 4, "text": "Op de mat!"}]
        diff = [{"start": 0, "end": 2, "text": "de rat zit"}, {"start": 2, "end": 4, "text": "op de mat"}]
        self.assertTrue(D.circularity(ref, same)["circular"])
        self.assertFalse(D.circularity(ref, diff)["circular"])
        self.assertAlmostEqual(D.circularity(ref, diff)["ratio"], 0.5)


class RoleChecks(unittest.TestCase):
    ROLES = {"A": "docent", "B": "leerling"}

    def setUp(self):
        self.ref = make_ref([dict(start=0, end=10, spk="A", role="docent"), dict(start=10, end=20, spk="B", role="leerling")])
        self.turns = [{"start": 0, "end": 10, "docent_role": "DOCENT"},     # goed
                      {"start": 10, "end": 15, "docent_role": "ONZEKER"},   # onzeker
                      {"start": 15, "end": 20, "docent_role": "DOCENT"},    # fout
                      {"start": 8, "end": 12, "docent_role": "OTHER"},      # gemengde referentie (2 s docent, 2 s leerling)
                      {"start": 25, "end": 28, "docent_role": "OTHER"}]     # geen referentiespraak

    def test_8_onzeker_is_reported_separately_never_filtered(self):
        r = D.score_docent_roles(self.turns, self.ref, 30.0, self.ROLES)
        m = r["matrix_ref_role_by_pred"]
        self.assertEqual(m["leerling"]["ONZEKER"]["turns"], 1)
        self.assertEqual(m["leerling"]["DOCENT"]["turns"], 1)
        self.assertEqual(m["docent"]["DOCENT"]["turns"], 1)
        self.assertEqual(m["mixed"]["OTHER"]["turns"], 1)
        self.assertEqual(m["none"]["OTHER"]["turns"], 1)
        self.assertEqual(sum(c["turns"] for row in m.values() for c in row.values()), len(self.turns))   # niets weggefilterd
        self.assertEqual((r["scored_turns"], r["decided_turns"], r["onzeker_turns"]), (3, 2, 1))
        self.assertAlmostEqual(r["decided_accuracy"], 0.5)                     # 1 goed (t1), 1 fout (t3)
        self.assertAlmostEqual(r["coverage"], 2 / 3)
        self.assertAlmostEqual(r["strict_accuracy_onzeker_counts_wrong"], 1 / 3)

    def test_all_correct_gives_one_and_all_wrong_gives_zero(self):
        good = [{"start": 0, "end": 10, "docent_role": "DOCENT"}, {"start": 10, "end": 20, "docent_role": "OTHER"}]
        bad = [{"start": 0, "end": 10, "docent_role": "OTHER"}, {"start": 10, "end": 20, "docent_role": "DOCENT"}]
        self.assertEqual(D.score_docent_roles(good, self.ref, 20.0, self.ROLES)["decided_accuracy"], 1.0)
        self.assertEqual(D.score_docent_roles(bad, self.ref, 20.0, self.ROLES)["decided_accuracy"], 0.0)

    def test_not_evaluated_is_its_own_column(self):
        r = D.score_docent_roles([{"start": 0, "end": 10, "docent_role": None}], self.ref, 20.0, self.ROLES)
        self.assertEqual(r["matrix_ref_role_by_pred"]["docent"]["NIET_BEOORDEELD"]["turns"], 1)
        self.assertEqual(r["decided_turns"], 0)
        self.assertIsNone(r["decided_accuracy"])

    def test_no_reference_roles_is_explicit(self):
        self.assertEqual(D.score_docent_roles(self.turns, self.ref, 30.0, {})["status"], "no_reference_roles")


class ErrorAndSafetyChecks(unittest.TestCase):
    def test_9_missing_reference_has_clear_error(self):
        with self.assertRaises(R.ReferenceProblem) as cm:
            R.load_reference("/bestaat/niet/ref.csv")
        self.assertIn("ontbreekt", str(cm.exception))
        self.assertIn("ref.csv", str(cm.exception))

    def test_9_reference_missing_columns_and_bad_times(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.csv"
            p.write_text("a,b\n1,2\n", encoding="utf-8")
            with self.assertRaisesRegex(R.ReferenceProblem, "kolommen ontbreken"):
                R.load_reference(p)
            q = write_csv(d, [dict(start=5, end=3, spk="A")], "y.csv")
            with self.assertRaisesRegex(R.ReferenceProblem, "eindtijd"):
                R.load_reference(q)

    def test_9_unreadable_and_missing_audio(self):
        with tempfile.TemporaryDirectory() as d:
            bogus = Path(d) / "kapot.mp3"
            bogus.write_text("dit is geen audio", encoding="utf-8")
            with self.assertRaises(L.AudioUnreadableError) as cm:
                L.probe_audio(bogus)
            self.assertIn("niet leesbaar", str(cm.exception))
            with self.assertRaisesRegex(L.AudioUnreadableError, "ontbreekt"):
                L.probe_audio(Path(d) / "weg.mp3")

    def test_real_audio_is_readable_and_duration_plausible(self):
        self.assertAlmostEqual(L.probe_audio(S.TEST_FILES / "testaudio2_fragment.mp3"), 30.0, delta=0.1)

    def test_10_existing_output_dir_and_file_are_not_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            run = L.new_dir(Path(d) / "runs" / "r1")
            f = L.write_new(run / "out.json", "origineel")
            with self.assertRaises(L.OutputExistsError):
                L.new_dir(Path(d) / "runs" / "r1")
            with self.assertRaises(L.OutputExistsError):
                L.write_new(f, "nieuw")
            self.assertEqual(f.read_text(encoding="utf-8"), "origineel")

    def test_unintelligible_is_derived_warning_only_not_an_exclusion(self):
        ref = make_ref([dict(start=0, end=4, spk="A", intel="ja", text="onverstaanbaar stukje"),
                        dict(start=4, end=8, spk="B", intel="nee", text="duidelijk")])
        self.assertEqual([r.unintelligible for r in ref.rows], ["ja", "nee"])
        self.assertEqual([r.unintelligible for r in ref.rows], [r.intelligible for r in ref.rows])
        self.assertIn("onverstaanbaar", R.reference_text(ref))                        # blijft in de tekst
        self.assertAlmostEqual(sum(s.duration for s in R.build_uem(ref, 8, "labelled", "keep")), 8.0)   # blijft in de UEM

    def test_run_original_main_patches_restores_and_records_failures(self):
        import types
        m = types.ModuleType("fakestage")
        m.OUT = "origineel"

        def main():
            import sys
            print("args", sys.argv[1:], m.OUT)
            if "--exit" in sys.argv:
                raise SystemExit("kapot")
            if "--boom" in sys.argv:
                raise ValueError("boem")
        m.main = main
        with tempfile.TemporaryDirectory() as d:
            ok = L.run_original_main(m, ["a"], {"OUT": "omgeleid"}, Path(d) / "ok.log")
            self.assertEqual((ok["status"], m.OUT), ("ok", "origineel"))              # hersteld
            self.assertIn("omgeleid", ok["stdout"])
            ex = L.run_original_main(m, ["--exit"], {"OUT": "x"})
            self.assertEqual((ex["status"], ex["detail"]), ("exit", "kapot"))
            er = L.run_original_main(m, ["--boom"], {"OUT": "x"})
            self.assertEqual(er["status"], "error")
            self.assertIn("ValueError", er["detail"])
            with self.assertRaises(L.OutputExistsError):                              # logbestand wordt ook niet overschreven
                L.run_original_main(m, ["a"], {}, Path(d) / "ok.log")


class RealReferenceChecks(unittest.TestCase):
    """Parseert de echte referenties (alleen lezen) en controleert de aannames van het protocol."""

    def load(self, name):
        return R.load_reference(S.GT_DIR / name, name)

    def test_originals_are_not_modified_by_loading(self):
        files = sorted(S.GT_DIR.glob("ground_truth_*.csv"))
        before = {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in files}
        for f in files:
            if "template" not in f.name:
                R.load_reference(f)
        self.assertEqual(before, {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in files})

    def test_known_facts_per_file(self):
        t4 = self.load("ground_truth_testaudio4_fragment.csv")
        self.assertEqual((len(t4.rows), t4.speakers()), (87, ["SPREKER_A", "SPREKER_B", "SPREKER_C", "SPREKER_D"]))
        t5 = self.load("ground_truth_testaudio5_fragment.csv")
        self.assertEqual(t5.speakers(), ["SPREKER_A", "SPREKER_B", "SPREKER_C"])        # ONBEKEND is geen spreker
        self.assertEqual(sum(r.kind == "unknown" for r in t5.rows), 2)
        self.assertEqual(sum(r.kind == "cut" for r in t5.rows), 1)                       # 'niet meenemen'
        t1 = self.load("ground_truth_testaudio1_fragment.csv")
        self.assertEqual(sum(r.kind == "nonspeech" for r in t1.rows), 1)                 # APPLAUS
        self.assertFalse(self.load("ground_truth_final_testfragment.csv").has_speaker_labels)
        raster = self.load("ground_truth_testaudio2_fragment_raster.csv")
        self.assertEqual((len(raster.rows), raster.speakers()), (19, ["SPREKER_A", "SPREKER_B"]))
        self.assertTrue(all(r.role is None for r in raster.rows))                        # raster heeft geen rolkolom
        tracked = self.load("ground_truth_testaudio2_fragment.csv")
        self.assertEqual(R.speaker_roles(raster, R.speaker_roles(tracked)), {"SPREKER_A": "docent", "SPREKER_B": "leerling"})

    def test_testaudio5_cut_region_is_excluded_from_text_and_uem(self):
        t5 = self.load("ground_truth_testaudio5_fragment.csv")
        self.assertNotIn("fackie", R.reference_text(t5))
        self.assertLessEqual(max(s.end for s in R.build_uem(t5, 46.0, "strict", "keep")), 45.1 + 1e-9)


class MutationSensitivity(unittest.TestCase):
    """Bewijs dat de tests kunnen falen: met opzettelijk kapotte scorers MOETEN de echte tests mislukken."""

    @staticmethod
    def _fails(cls):
        import os
        with open(os.devnull, "w") as sink:
            res = unittest.TextTestRunner(stream=sink, verbosity=0).run(unittest.defaultTestLoader.loadTestsFromTestCase(cls))
        return not res.wasSuccessful()

    def test_kapotte_wer_wordt_ontdekt(self):
        with mock.patch.object(T, "edit_counts", lambda r, h: {"errors": 0, "substitutions": 0, "deletions": 0, "insertions": 0}):
            self.assertTrue(self._fails(TextChecks))

    def test_kapotte_der_wordt_ontdekt(self):
        with mock.patch.object(D, "compute_der", lambda *a, **k: {"status": "ok", "der": 0.0, "confusion_s": 0.0, "missed_s": 0.0,
                                                                   "false_alarm_s": 0.0, "total_ref_speech_s": 1.0}):
            self.assertTrue(self._fails(DerChecks))

    def test_rolscorer_die_onzeker_wegfiltert_wordt_ontdekt(self):
        real = D.score_docent_roles

        def filtering(turns, *a, **k):
            return real([t for t in turns if t.get("docent_role") != "ONZEKER"], *a, **k)
        with mock.patch.object(D, "score_docent_roles", filtering):
            self.assertTrue(self._fails(RoleChecks))

    def test_segmentscorer_die_alles_single_noemt_wordt_ontdekt(self):
        with mock.patch.object(S, "SEG_MIXED_MIN_SHARE", 2.0):                         # 'mixed' kan nooit meer optreden
            self.assertTrue(self._fails(SegmentChecks))


if __name__ == "__main__":
    unittest.main()
