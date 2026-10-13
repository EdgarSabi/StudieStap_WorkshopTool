"""Optionele stemconsistentie. Synthetische embeddings; geen echt model."""
from studiestap.alignment.speakers import couple_speakers
from studiestap.models import ReviewStatus, Segment, SegmentVoiceCheck, SpeakerInterval, Transcript
from studiestap.quality.checks import build_quality_report
from studiestap.recognition.voice_consistency import check_voice_consistency
from studiestap.settings import QualitySettings, Settings, load_settings

A, B = [1.0, 0.1], [0.1, 1.0]


def iv(s, a, b):
    return SpeakerInterval(s, a, b)


def embedder(by_start, calls=None):
    def f(start, end):
        if calls is not None:
            calls.append((start, end))
        return by_start.get(round(start))
    return f


def run(segments, intervals, emb):
    sp = couple_speakers([Segment(i, a, b, "x") for i, (a, b) in enumerate(segments)], intervals)
    return check_voice_consistency(sp, intervals, emb, 1.0), sp


# A spreekt 0-10, 20-30, 40-50 en 60-70 (referentiestukken, licht verschillend); B spreekt 80-90, 100-110, 120-130, 140-150.
BASE = [iv("A", 0, 10), iv("A", 20, 30), iv("A", 40, 50), iv("A", 60, 70),
        iv("B", 80, 90), iv("B", 100, 110), iv("B", 120, 130), iv("B", 140, 150)]
BASE_EMB = {0: [1.0, 0.1], 20: [1.0, 0.2], 40: [1.0, 0.0], 60: [1.0, 0.15],
            80: [0.1, 1.0], 100: [0.2, 1.0], 120: [0.0, 1.0], 140: [0.15, 1.0]}


def test_stem_die_bij_het_label_past_is_CONSISTENT():
    emb = embedder({**BASE_EMB, 160: [1.0, 0.1]})
    res, _ = run([(160, 163)], BASE + [iv("A", 160, 163)], emb)
    assert res[0].verdict == "CONSISTENT" and res[0].own_similarity > res[0].other_similarity


def test_stem_van_andere_spreker_wordt_alleen_gemeld_niet_aangepast():
    ivs = BASE + [iv("A", 160, 163)]
    res, sp = run([(160, 163)], ivs, embedder({**BASE_EMB, 160: [0.1, 1.0]}))
    assert res[0].verdict == "CLOSER_TO_OTHER_SPEAKER" and res[0].other_speaker == "B"
    assert sp[0].dominant_speaker == "A"                      # sprekerkoppeling blijft ongemoeid
    assert ivs == BASE + [iv("A", 160, 163)]                  # intervallen ongewijzigd


def test_dichter_bij_ander_label_maar_binnen_eigen_bereik_is_INCONCLUSIVE():
    # Het eigen stuk ligt dicht bij B, maar elk eigen referentiestuk is zelf ook zo ongelijk: geen schijnzeker oordeel.
    ivs = [iv("A", 0, 10), iv("A", 20, 30), iv("A", 40, 50), iv("A", 60, 70), iv("A", 160, 163),
           iv("B", 80, 90), iv("B", 100, 110), iv("B", 120, 130)]
    emb = {0: [1.0, 0.0], 20: [0.0, 1.0], 40: [0.7, 0.7], 60: [0.5, 0.9], 80: [0.1, 1.0], 100: [0.2, 1.0],
           120: [0.0, 1.0], 160: [0.2, 1.0]}
    res, _ = run([(160, 163)], ivs, embedder(emb))
    assert res[0].verdict == "INCONCLUSIVE" and res[0].own_similarity is not None


def test_te_kort_of_overlap_is_INCONCLUSIVE_zonder_embedding():
    calls = []
    ivs = BASE + [iv("A", 160, 160.5), iv("A", 170, 173), iv("B", 170, 173)]
    res, _ = run([(160, 160.5), (170, 173)], ivs, embedder(BASE_EMB, calls))
    assert [r.verdict for r in res] == ["INCONCLUSIVE", "INCONCLUSIVE"]
    assert not any(c[0] >= 160 for c in calls)               # niets onzekers geembed


def test_zonder_andere_sprekers_of_te_weinig_stukken_is_INCONCLUSIVE():
    only_a = [iv("A", 0, 10), iv("A", 20, 30), iv("A", 40, 50), iv("A", 160, 163)]
    res, _ = run([(160, 163)], only_a, embedder({0: A, 20: A, 40: A, 160: B}))
    assert res[0].verdict == "INCONCLUSIVE"
    few = [iv("A", 0, 10), iv("A", 160, 163), iv("B", 80, 90)]
    res, _ = run([(160, 163)], few, embedder({0: A, 80: B, 160: B}))
    assert res[0].verdict == "INCONCLUSIVE"


def test_segment_telt_niet_mee_in_zijn_eigen_profiel():
    # Het segment ligt binnen het referentiestuk 160-200 van A. Zonder uitsluiting zou dat stuk het eigen profiel beinvloeden.
    ivs = BASE + [iv("A", 160, 200)]
    calls = []
    res, _ = run([(160, 163)], ivs, embedder({**BASE_EMB, 160: [0.1, 1.0]}, calls))
    assert res[0].verdict == "CLOSER_TO_OTHER_SPEAKER"


def test_embedding_mislukt_is_INCONCLUSIVE():
    res, _ = run([(160, 163)], BASE + [iv("A", 160, 163)], embedder(BASE_EMB))
    assert res[0].verdict == "INCONCLUSIVE" and "geembed" in res[0].reason


# ---------------------------------------------------------------- kwaliteit en instelling
def test_alleen_CLOSER_geeft_signaal_en_REVIEW_REQUIRED():
    t = Transcript("nl", 3.0, "m", {}, 0.0, [Segment(0, 0, 1, "a"), Segment(1, 1, 2, "b"), Segment(2, 2, 3, "c")])
    checks = [SegmentVoiceCheck(0, "A", "CONSISTENT"), SegmentVoiceCheck(1, "A", "INCONCLUSIVE", "x"),
              SegmentVoiceCheck(2, "A", "CLOSER_TO_OTHER_SPEAKER", "x", 0.1, "B", 0.6, 0.4)]
    q = build_quality_report(t, None, None, None, QualitySettings(), checks)
    assert [s.status for s in q.segments] == [ReviewStatus.ASSESSABLE, ReviewStatus.ASSESSABLE,
                                               ReviewStatus.REVIEW_REQUIRED]
    assert [x.code for x in q.segments[2].signals] == ["VOICE_CLOSER_TO_OTHER_SPEAKER"]
    assert all(x.kind == "observed" for x in q.segments[2].signals)


def test_standaard_uit_en_aan_te_zetten_via_config(tmp_path):
    assert Settings().voice_consistency.enabled is False
    cfg = tmp_path / "c.yaml"
    cfg.write_text("voice_consistency:\n  enabled: true\n", encoding="utf-8")
    assert load_settings(cfg).voice_consistency.enabled is True
