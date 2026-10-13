"""Mijlpaal B: sprekerkoppeling (pure tijdrekenkunde, synthetische gegevens).

Eigenschap die we bewaken: ruwe sprekerinformatie wordt NOOIT stilzwijgend weggegooid,
en bij twijfel wordt niets verzonnen.
"""
import random

from studiestap.alignment.speakers import couple_speakers
from studiestap.models import (AlignedSegment, Segment, SpeakerInterval, StepStatus, Word, WordAlignment)


def seg(i=0, start=0.0, end=4.0, text="x"):
    return Segment(id=i, start=start, end=end, text=text)


def iv(speaker, start, end):
    return SpeakerInterval(speaker=speaker, start=start, end=end)


def one(segment, intervals, alignment=None):
    return couple_speakers([segment], intervals, alignment)[0]


# ---------------------------------------------------------------- normale gevallen
def test_een_spreker_dekt_het_hele_segment():
    # Verwacht: SINGLE, dominant A met aandeel 1.0, 1 intersectie.
    r = one(seg(), [iv("A", 0, 4)])
    assert (r.attribution, r.dominant_speaker, r.dominant_share) == ("SINGLE", "A", 1.0)
    assert len(r.intersections) == 1 and r.simultaneous_seconds == 0


def test_sprekerwissel_binnen_segment_bewaart_beide_en_kiest_bij_gelijkspel_niet():
    # Verwacht: A 0-2, B 2-4 in segment 0-4 -> MIXED, beide intersecties, geen dominante spreker (gelijkspel).
    r = one(seg(), [iv("A", 0, 2), iv("B", 2, 4)])
    assert r.attribution == "MIXED"
    assert [(x.speaker, x.start, x.end) for x in r.intersections] == [("A", 0, 2), ("B", 2, 4)]
    assert r.dominant_speaker is None and r.simultaneous_seconds == 0


def test_dominante_spreker_is_alleen_samenvatting_de_rest_blijft_bewaard():
    # Verwacht: A 3 s, B 1 s -> dominant A (0.75), maar B's intersectie staat er nog.
    r = one(seg(), [iv("A", 0, 3), iv("B", 3, 4)])
    assert (r.dominant_speaker, r.dominant_share) == ("A", 0.75)
    assert {x.speaker for x in r.intersections} == {"A", "B"}
    assert r.seconds_per_speaker == {"A": 3.0, "B": 1.0}


def test_echte_gelijktijdige_spraak_wordt_gemeten():
    # Verwacht: A 0-4 en B 1-3 -> 2 s tegelijk, MIXED, beide intersecties.
    r = one(seg(), [iv("A", 0, 4), iv("B", 1, 3)])
    assert r.simultaneous_seconds == 2.0 and r.attribution == "MIXED"
    assert len(r.intersections) == 2


def test_zelfde_spreker_met_overlappende_intervallen_wordt_niet_dubbel_geteld():
    # Verwacht: A 0-3 en A 2-4 -> samen 4 s (niet 5), geen 'gelijktijdige' spraak want maar een spreker.
    r = one(seg(), [iv("A", 0, 3), iv("A", 2, 4)])
    assert r.seconds_per_speaker == {"A": 4.0}
    assert r.simultaneous_seconds == 0 and r.attribution == "SINGLE"
    assert len(r.intersections) == 2  # ruwe intersecties blijven allebei bestaan


def test_gedeeltelijke_dekking_is_PARTIAL_en_stilte_wordt_gemeld():
    r = one(seg(), [iv("A", 0, 1)])
    assert r.attribution == "PARTIAL" and r.uncovered_seconds == 3.0


# ---------------------------------------------------------------- tegenvoorbeelden
def test_geen_overlap_geeft_NONE_en_geen_verzonnen_spreker():
    r = one(seg(), [iv("A", 10, 12)])
    assert r.attribution == "NONE" and r.intersections == [] and r.dominant_speaker is None
    assert r.uncovered_seconds == 4.0


def test_rakende_grens_is_geen_intersectie():
    # Verwacht: interval eindigt precies waar het segment begint -> 0 s overlap -> geen intersectie.
    r = one(seg(start=2, end=4), [iv("A", 0, 2)])
    assert r.intersections == []


def test_segment_met_nul_duur_crasht_niet():
    r = one(seg(start=1, end=1), [iv("A", 0, 2)])
    assert r.attribution == "NONE" and r.dominant_speaker is None


def test_lege_diarizatie():
    r = one(seg(), [])
    assert r.attribution == "NONE"


def test_invoer_wordt_niet_gewijzigd_en_volgorde_van_invoer_maakt_niet_uit():
    ivs = [iv("B", 2, 4), iv("A", 0, 2)]
    before = [(i.speaker, i.start, i.end) for i in ivs]
    a = one(seg(), ivs)
    b = one(seg(), list(reversed(ivs)))
    assert [(i.speaker, i.start, i.end) for i in ivs] == before
    assert a == b


def test_lossless_eigenschap_elk_overlappend_interval_staat_er_precies_een_keer_in():
    # Eigenschap over 200 willekeurige (vaste seed) situaties: aantal intersecties == aantal
    # intervallen met positieve overlap, en elke intersectie ligt binnen het segment en het interval.
    rng = random.Random(1234)
    for _ in range(200):
        ivs = []
        for _ in range(rng.randint(0, 8)):
            s = rng.uniform(-1, 6)
            ivs.append(iv(rng.choice("ABC"), s, s + rng.uniform(0.05, 3)))
        segment = seg(start=1.0, end=4.0)
        r = one(segment, ivs)
        expected = sum(1 for i in ivs if min(i.end, 4.0) > max(i.start, 1.0))
        assert len(r.intersections) == expected
        for x in r.intersections:
            assert 1.0 <= x.start < x.end <= 4.0
            assert abs(x.duration - (x.end - x.start)) < 1e-9


# ---------------------------------------------------------------- woordniveau
def alignment(words, status=StepStatus.SUCCEEDED, seg_status=StepStatus.SUCCEEDED):
    return WordAlignment(status, "", segments=[AlignedSegment(0, words, seg_status)])


def test_woord_binnen_een_spreker_wordt_SINGLE():
    r = one(seg(), [iv("A", 0, 2), iv("B", 2, 4)], alignment([Word("hoi", 0.2, 0.8)]))
    assert (r.words[0].status, r.words[0].speaker) == ("SINGLE", "A")


def test_woord_over_sprekerwissel_is_AMBIGUOUS_en_krijgt_geen_spreker():
    r = one(seg(), [iv("A", 0, 2), iv("B", 2, 4)], alignment([Word("dag", 1.8, 2.3)]))
    w = r.words[0]
    assert w.status == "AMBIGUOUS" and w.speaker is None and w.candidates == ["A", "B"]


def test_woord_zonder_tijd_is_NO_TIMING_niets_verzonnen():
    r = one(seg(), [iv("A", 0, 4)], alignment([Word("2024", None, None)], StepStatus.PARTIAL))
    assert r.words[0].status == "NO_TIMING" and r.words[0].speaker is None


def test_woord_in_stilte_is_NO_SPEAKER():
    r = one(seg(), [iv("A", 0, 1)], alignment([Word("ja", 3.0, 3.4)]))
    assert r.words[0].status == "NO_SPEAKER"


def test_woord_van_nul_lengte_op_sprekerwissel_is_ambigu():
    r = one(seg(), [iv("A", 0, 2), iv("B", 2, 4)], alignment([Word("eh", 2.0, 2.0)]))
    assert r.words[0].status == "AMBIGUOUS"


def test_zonder_beschikbare_uitlijning_geen_woorden_maar_segment_blijft_intact():
    for al in (None, WordAlignment(StepStatus.UNAVAILABLE, "geen whisperx"),
               WordAlignment(StepStatus.FAILED, "crash")):
        r = one(seg(), [iv("A", 0, 4)], al)
        assert r.words == [] and r.attribution == "SINGLE"


def test_ontbrekende_woorden_in_uitlijning_geeft_lege_woordenlijst():
    r = one(seg(), [iv("A", 0, 4)], alignment([], StepStatus.FAILED, StepStatus.FAILED))
    assert r.words == []
