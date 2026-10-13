"""Mijlpaal C: docentherkenning (identiteit vs rol) en kwaliteitssignalen. Synthetische gegevens."""
from studiestap.models import (ReviewStatus, Segment, SegmentSpeakers, SpeakerInterval, StepStatus,
                               Transcript, AlignedSegment, Word, WordAlignment, SpeakerRole, Intersection)
from studiestap.quality.checks import build_quality_report
from studiestap.recognition.teacher import exclusive_parts, no_reference_roles, recognize_teacher
from studiestap.settings import QualitySettings, TeacherSettings
from studiestap.alignment.speakers import couple_speakers


def iv(s, a, b):
    return SpeakerInterval(s, a, b)


REF = [1.0, 0.0]


def embedder(by_start):
    """Nep-embedder: de vector hangt af van waar het stuk begint (zo sturen we de gelijkenis per spreker)."""
    return lambda start, end: by_start.get(round(start))


# ---------------------------------------------------------------- docentherkenning
def test_match_no_match_en_rol_zijn_gescheiden():
    # A klinkt als de referentie, B niet. Verwacht: A MATCH/docent, B NO_MATCH/onbekend (niet 'leerling').
    ivs = [iv("A", 0, 10), iv("B", 20, 30)]
    emb = embedder({0: [1.0, 0.0], 20: [0.0, 1.0]})
    roles = {r.speaker: r for r in recognize_teacher(ivs, REF, emb, TeacherSettings())}
    assert (roles["A"].identity_status, roles["A"].role) == ("MATCH", "docent")
    assert (roles["B"].identity_status, roles["B"].role) == ("NO_MATCH", "onbekend")


def test_spreker_id_is_niet_automatisch_docent_zonder_referentie():
    roles = no_reference_roles([iv("SPEAKER_00", 0, 50), iv("SPEAKER_01", 50, 60)])
    assert {r.identity_status for r in roles} == {"NO_REFERENCE"} and {r.role for r in roles} == {"onbekend"}


def test_te_korte_stukken_geven_UNKNOWN_niet_NO_MATCH():
    roles = recognize_teacher([iv("A", 0, 0.5)], REF, embedder({0: [1.0, 0.0]}), TeacherSettings(min_clip_seconds=1.0))
    assert roles[0].identity_status == "UNKNOWN" and roles[0].similarity is None


def test_niet_te_embedden_audio_is_UNKNOWN_en_geen_bewijs_tegen():
    roles = recognize_teacher([iv("A", 0, 10)], REF, lambda s, e: None, TeacherSettings())
    assert roles[0].identity_status == "UNKNOWN" and roles[0].n_clips == 0


def test_drempel_grens_is_experimenteel_maar_deterministisch():
    # sim = 0.35 precies -> MATCH (>=), net eronder -> NO_MATCH.
    at = [0.35, (1 - 0.35 ** 2) ** 0.5]
    below = [0.349, (1 - 0.349 ** 2) ** 0.5]
    assert recognize_teacher([iv("A", 0, 5)], REF, lambda s, e: at, TeacherSettings())[0].identity_status == "MATCH"
    assert recognize_teacher([iv("A", 0, 5)], REF, lambda s, e: below, TeacherSettings())[0].identity_status == "NO_MATCH"


def test_mediaan_negeert_een_uitschieter():
    ivs = [iv("A", 0, 5), iv("A", 10, 15), iv("A", 20, 25)]
    emb = embedder({0: [1.0, 0.0], 10: [1.0, 0.0], 20: [-1.0, 0.0]})
    r = recognize_teacher(ivs, REF, emb, TeacherSettings())[0]
    assert r.identity_status == "MATCH" and r.n_clips == 3


def test_overlappende_spraak_wordt_niet_geembed():
    # A 0-4 en B 1-2: voor A blijven (0,1) en (2,4) over; (1,2) is mengspraak.
    assert exclusive_parts(iv("A", 0, 4), [iv("A", 0, 4), iv("B", 1, 2)]) == [(0, 1), (2, 4)]
    assert exclusive_parts(iv("A", 1, 2), [iv("A", 1, 2), iv("B", 0, 4)]) == []   # volledig overlapt


def test_volledig_overlappende_spreker_wordt_niet_op_mengstem_beoordeeld():
    ivs = [iv("A", 0, 10), iv("B", 0, 10)]   # twee sprekers precies tegelijk
    roles = recognize_teacher(ivs, REF, lambda s, e: [1.0, 0.0], TeacherSettings())
    assert {r.identity_status for r in roles} == {"UNKNOWN"}


# ---------------------------------------------------------------- kwaliteit
def transcript(*segs):
    return Transcript("nl", 10.0, "m", {}, 0.0, list(segs))


def report(t, ivs=None, alignment=None, roles=None):
    speakers = couple_speakers(t.segments, ivs, alignment) if ivs is not None else None
    return build_quality_report(t, speakers, alignment, roles, QualitySettings())


def codes(rep, i):
    return {s.code for s in rep.segments[i].signals}


def test_schone_situatie_geeft_geen_signalen_maar_ook_geen_bewijs():
    t = transcript(Segment(0, 0, 4, "dit is helder", -0.2, 0.01, 1.2))
    al = WordAlignment(StepStatus.SUCCEEDED, "", segments=[AlignedSegment(0, [Word("dit", 0, 1)])])
    roles = [SpeakerRole("A", "MATCH", "docent", 0.8, 3)]
    rep = report(t, [iv("A", 0, 4)], al, roles)
    assert rep.segments[0].status == ReviewStatus.ASSESSABLE and rep.segments[0].signals == []
    assert "geen bewijs" in rep.note.lower() or "geen signalen" in rep.note.lower()


def test_asr_signalen_gebruiken_de_whisper_standaardwaarden():
    t = transcript(Segment(0, 0, 4, "hm", -1.5, 0.9, 3.0))
    c = codes(report(t, [iv("A", 0, 4)]), 0)
    assert {"ASR_LOW_AVG_LOGPROB", "ASR_HIGH_NO_SPEECH_PROB", "ASR_HIGH_COMPRESSION_RATIO"} <= c
    # grens: exact op de drempel is nog geen signaal
    t2 = transcript(Segment(0, 0, 4, "hm", -1.0, 0.6, 2.4))
    assert not (codes(report(t2, [iv("A", 0, 4)]), 0) & {"ASR_LOW_AVG_LOGPROB", "ASR_HIGH_NO_SPEECH_PROB",
                                                          "ASR_HIGH_COMPRESSION_RATIO"})


def test_sprekersignalen_mixed_overlap_geen_spreker():
    t = transcript(Segment(0, 0, 4, "a"), Segment(1, 10, 14, "b"))
    rep = report(t, [iv("A", 0, 4), iv("B", 1, 3)])
    assert {"SPEAKER_MIXED", "POSSIBLE_SIMULTANEOUS_SPEECH"} <= codes(rep, 0)
    assert "SPEAKER_NONE" in codes(rep, 1)
    assert rep.segments[0].status == ReviewStatus.REVIEW_REQUIRED


def test_ambigue_woorden_en_ontbrekende_uitlijning_worden_gemeld():
    t = transcript(Segment(0, 0, 4, "een twee"))
    al = WordAlignment(StepStatus.PARTIAL, "", segments=[AlignedSegment(
        0, [Word("een", 1.5, 2.5), Word("twee", None, None)], StepStatus.PARTIAL)])
    rep = report(t, [iv("A", 0, 2), iv("B", 2, 4)], al)
    assert {"AMBIGUOUS_WORD_SPEAKERS", "WORDS_NOT_FULLY_ALIGNED"} <= codes(rep, 0)
    assert any(g.code == "WORD_ALIGNMENT_PARTIAL" for g in rep.global_signals)
    rep2 = report(t, [iv("A", 0, 4)], WordAlignment(StepStatus.UNAVAILABLE, "x"))
    assert any(g.code == "WORD_ALIGNMENT_UNAVAILABLE" for g in rep2.global_signals)


def test_onbekende_docentidentiteit_is_signaal_maar_NO_MATCH_niet():
    t = transcript(Segment(0, 0, 4, "tekst"))
    unk = report(t, [iv("A", 0, 4)], roles=no_reference_roles([iv("A", 0, 4)]))
    assert "SPEAKER_IDENTITY_UNKNOWN" in codes(unk, 0)
    assert any(g.code == "NO_TEACHER_REFERENCE" for g in unk.global_signals)
    nomatch = report(t, [iv("A", 0, 4)], roles=[SpeakerRole("A", "NO_MATCH", "onbekend", 0.1, 2)])
    assert "SPEAKER_IDENTITY_UNKNOWN" not in codes(nomatch, 0)


def test_meerdere_docentmatches_wordt_gemeld():
    t = transcript(Segment(0, 0, 4, "tekst"))
    roles = [SpeakerRole("A", "MATCH", "docent", 0.9, 2), SpeakerRole("B", "MATCH", "docent", 0.8, 2)]
    assert any(g.code == "MULTIPLE_TEACHER_MATCHES" for g in report(t, [iv("A", 0, 4)], roles=roles).global_signals)


def test_lege_tekst_is_NOT_ASSESSABLE_en_ontbrekende_diarizatie_is_globaal_signaal():
    t = transcript(Segment(0, 0, 4, "   "))
    rep = report(t)
    assert rep.segments[0].status == ReviewStatus.NOT_ASSESSABLE
    assert any(g.code == "DIARIZATION_MISSING" for g in rep.global_signals)


def test_alle_signalen_zijn_waarnemingen_nooit_bewezen_onbetrouwbaar():
    t = transcript(Segment(0, 0, 4, "", -3, 0.99, 9))
    rep = report(t, [iv("A", 0, 1), iv("B", 0, 4)], WordAlignment(StepStatus.FAILED, "x"))
    every = rep.global_signals + [s for q in rep.segments for s in q.signals]
    assert every and all(s.kind == "observed" for s in every)
