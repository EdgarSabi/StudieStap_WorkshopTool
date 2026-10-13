"""Mijlpaal B/C: de hele pipeline met nep-modellen (integratietests, synthetische audio).

Bewaakt: geen dubbele modeluitvoering, gecontroleerd doorgaan bij falende stappen,
behoud van ruwe tijdlijnen, tekst blijft bewaard, geen geheimen of audio in de uitvoer.
"""
import json

import pytest

from conftest import make_wav, needs_ffmpeg
from studiestap.models import (Diarization, Segment, SpeakerInterval, SpeakerRole, StepStatus, StudieStapError,
                               Transcript, Word, AlignedSegment, WordAlignment)
from studiestap.pipeline import Backends, Reporter, run_pipeline
from studiestap.settings import Settings

pytestmark = needs_ffmpeg


class Counter:
    def __init__(self):
        self.transcribe = self.diarize = self.align = 0


def make_backends(counter, *, diar_fails=False, align_status=StepStatus.SUCCEEDED, transcribe_fails=False,
                  empty_segment=False):
    segs = [Segment(0, 0.0, 2.0, "welkom allemaal", -0.2, 0.01, 1.1),
            Segment(1, 2.0, 4.0, "" if empty_segment else "vragen jullie dat", -1.5, 0.02, 1.0)]

    def transcribe(wav, s):
        counter.transcribe += 1
        if transcribe_fails:
            raise StudieStapError("Whisper stuk.", hint="Probeer opnieuw.")
        return Transcript("nl", 4.0, "fake", {}, 0.1, segs)

    def diarize(wav, s):
        counter.diarize += 1
        if diar_fails:
            raise StudieStapError("Pyannote stuk.")
        return Diarization("fake", "m", {}, 0.1, [SpeakerInterval("SPEAKER_00", 0.0, 2.5),
                                                  SpeakerInterval("SPEAKER_01", 2.0, 4.0)])  # overlap 2.0-2.5

    def align(t, wav, s):
        counter.align += 1
        if align_status in (StepStatus.UNAVAILABLE, StepStatus.FAILED):
            return WordAlignment(align_status, "geen alignment")
        return WordAlignment(StepStatus.SUCCEEDED, "ok", segments=[
            AlignedSegment(0, [Word("welkom", 0.1, 0.9), Word("allemaal", 1.0, 1.9)]),
            AlignedSegment(1, [Word("vragen", 2.1, 2.6), Word("jullie", 2.7, 3.0), Word("dat", 3.1, 3.9)])])

    def recognize(diar, wav, ref_wav, s):
        return [SpeakerRole("SPEAKER_00", "MATCH", "docent", 0.6, 3),
                SpeakerRole("SPEAKER_01", "NO_MATCH", "onbekend", 0.1, 2)]

    return Backends(transcribe=transcribe, diarize=diarize, align=align, recognize=recognize)


@pytest.fixture
def setup(tmp_path):
    audio = make_wav(tmp_path / "opname.wav", seconds=4.0, rate=16000, channels=1)
    settings = Settings()
    settings.output.directory = str(tmp_path / "out")
    return audio, settings


def load(report, name):
    return json.loads((report.run_dir / name).read_text(encoding="utf-8"))


def test_volledige_run_schrijft_alle_deelbestanden_en_behoudt_ruwe_tijdlijn(setup):
    audio, settings = setup
    r = run_pipeline(audio, settings, backends=make_backends(Counter()))
    assert r.ok
    for f in ["01_transcript.json", "02_diarization_raw.json", "03_word_alignment.json",
              "04_speaker_assignment.json", "05_teacher_roles.json", "06_quality.json", "07_result.json",
              "run_manifest.json"]:
        assert (r.run_dir / f).is_file(), f
    raw = load(r, "02_diarization_raw.json")
    assert len(raw["intervals"]) == 2                          # beide ruwe intervallen, incl. overlap
    result = load(r, "07_result.json")
    seg1 = result["segments"][1]["speakers"]
    assert {x["speaker"] for x in seg1["intersections"]} == {"SPEAKER_00", "SPEAKER_01"}   # niets weggegooid
    assert seg1["simultaneous_seconds"] == 0.5
    assert result["raw_speakers"] == ["SPEAKER_00", "SPEAKER_01"]
    # herleidbaarheid: hashes in het eindresultaat kloppen met de deelbestanden
    import hashlib
    for part in result["provenance"]["parts"].values():
        assert part["sha256"] == hashlib.sha256((r.run_dir / part["file"]).read_bytes()).hexdigest()


def test_tweede_run_voert_dure_modellen_niet_opnieuw_uit(setup):
    audio, settings = setup
    c = Counter()
    run_pipeline(audio, settings, backends=make_backends(c))
    r2 = run_pipeline(audio, settings, backends=make_backends(c))
    assert (c.transcribe, c.diarize, c.align) == (1, 1, 1)
    assert [s.reused_from_cache for s in r2.steps if s.name in ("transcription", "diarization", "word_alignment")] \
        == [True, True, True]


def test_veranderde_instelling_of_force_rekent_opnieuw(setup):
    audio, settings = setup
    c = Counter()
    run_pipeline(audio, settings, backends=make_backends(c))
    settings.transcription.beam_size = 1                 # andere instelling -> nieuwe transcriptie
    run_pipeline(audio, settings, backends=make_backends(c))
    assert c.transcribe == 2 and c.diarize == 1          # diarizatie-instellingen ongewijzigd
    run_pipeline(audio, settings, backends=make_backends(c), force=True)
    assert (c.transcribe, c.diarize) == (3, 2)


def test_kapotte_cache_wordt_genegeerd(setup):
    audio, settings = setup
    c = Counter()
    r = run_pipeline(audio, settings, backends=make_backends(c))
    (r.run_dir / "01_transcript.json").write_text("{kapot", encoding="utf-8")
    run_pipeline(audio, settings, backends=make_backends(c))
    assert c.transcribe == 2


def test_diarizatie_faalt_pipeline_gaat_door_zonder_sprekers_maar_met_tekst(setup):
    audio, settings = setup
    r = run_pipeline(audio, settings, backends=make_backends(Counter(), diar_fails=True))
    assert r.ok
    by = {s.name: s for s in r.steps}
    assert by["diarization"].status == StepStatus.FAILED and "Pyannote stuk" in by["diarization"].message
    assert by["speaker_assignment"].status == StepStatus.UNAVAILABLE
    result = load(r, "07_result.json")
    assert [s["text"] for s in result["segments"]] == ["welkom allemaal", "vragen jullie dat"]
    assert all(s["speakers"] is None for s in result["segments"])
    assert any(g["code"] == "DIARIZATION_MISSING" for g in result["quality"]["global_signals"])


@pytest.mark.parametrize("status", [StepStatus.UNAVAILABLE, StepStatus.FAILED])
def test_alignment_niet_beschikbaar_of_mislukt_valt_terug_op_segmentniveau(setup, status):
    audio, settings = setup
    r = run_pipeline(audio, settings, backends=make_backends(Counter(), align_status=status))
    assert r.ok
    assert load(r, "03_word_alignment.json")["status"] == status.value        # status wordt vastgelegd
    result = load(r, "07_result.json")
    assert all(s["speakers"]["words"] == [] for s in result["segments"])        # geen woordclaims
    assert result["segments"][0]["speakers"]["attribution"] in ("SINGLE", "PARTIAL", "MIXED")
    assert result["steps"]["word_alignment"]["status"] == status.value


def test_no_align_vlag_slaat_alignment_over(setup):
    audio, settings = setup
    c = Counter()
    r = run_pipeline(audio, settings, backends=make_backends(c), skip_alignment=True)
    assert c.align == 0
    assert {s.name: s.status for s in r.steps}["word_alignment"] == StepStatus.SKIPPED


def test_transcriptie_faalt_stopt_met_vriendelijke_status_zonder_eindresultaat(setup):
    audio, settings = setup
    r = run_pipeline(audio, settings, backends=make_backends(Counter(), transcribe_fails=True))
    assert not r.ok and r.result_path is None
    assert r.steps[0].status == StepStatus.FAILED and "Whisper stuk" in r.steps[0].message
    assert not (r.run_dir / "07_result.json").exists()
    assert json.loads((r.run_dir / "run_manifest.json").read_text())["overall"] == "failed"


def test_transcribe_modus_doet_alleen_transcriptie(setup):
    audio, settings = setup
    c = Counter()
    r = run_pipeline(audio, settings, mode="transcribe", backends=make_backends(c))
    assert r.ok and (c.transcribe, c.diarize, c.align) == (1, 0, 0)
    assert not (r.run_dir / "02_diarization_raw.json").exists()


def test_geen_referentie_geeft_NO_REFERENCE_en_geen_docentrol(setup):
    audio, settings = setup
    r = run_pipeline(audio, settings, backends=make_backends(Counter()))
    roles = load(r, "05_teacher_roles.json")
    assert {x["identity_status"] for x in roles} == {"NO_REFERENCE"}
    assert {x["role"] for x in roles} == {"onbekend"}          # SPEAKER_00 is NIET automatisch docent
    assert {s.name: s.status for s in r.steps}["teacher_roles"] == StepStatus.SKIPPED


def test_met_referentie_identiteit_en_rol_zijn_gescheiden_en_tekst_blijft_bij_onzekere_rol(setup, tmp_path):
    audio, settings = setup
    ref = make_wav(tmp_path / "docent.wav", seconds=2.0, rate=16000, channels=1)
    r = run_pipeline(audio, settings, backends=make_backends(Counter()), teacher_reference=ref)
    result = load(r, "07_result.json")
    roles = {x["speaker"]: x for x in result["speaker_roles"]}
    assert roles["SPEAKER_00"]["identity_status"] == "MATCH" and roles["SPEAKER_00"]["role"] == "docent"
    assert roles["SPEAKER_01"]["identity_status"] == "NO_MATCH" and roles["SPEAKER_01"]["role"] == "onbekend"
    assert all(s["text"] for s in result["segments"])


def test_herkenning_mislukt_wordt_UNKNOWN_en_niet_NO_MATCH(setup, tmp_path):
    audio, settings = setup
    ref = make_wav(tmp_path / "docent.wav", seconds=2.0, rate=16000, channels=1)
    b = make_backends(Counter())
    b.recognize = lambda *a: (_ for _ in ()).throw(StudieStapError("model weg"))
    r = run_pipeline(audio, settings, backends=b, teacher_reference=ref)
    assert r.ok
    result = load(r, "07_result.json")
    assert {x["identity_status"] for x in result["speaker_roles"]} == {"UNKNOWN"}


def test_lege_tekst_wordt_NOT_ASSESSABLE_maar_segment_blijft_staan(setup):
    audio, settings = setup
    r = run_pipeline(audio, settings, backends=make_backends(Counter(), empty_segment=True))
    seg = load(r, "07_result.json")["segments"][1]
    assert seg["quality"]["status"] == "NOT_ASSESSABLE" and seg["text"] == ""


def test_werkaudio_wordt_standaard_verwijderd_en_origineel_blijft(setup):
    audio, settings = setup
    voor = audio.read_bytes()
    r = run_pipeline(audio, settings, backends=make_backends(Counter()))
    assert not (r.run_dir / "work").exists()
    assert audio.read_bytes() == voor
    assert not list(r.run_dir.rglob("*.wav"))
    settings.output.keep_audio = True
    r2 = run_pipeline(audio, settings, backends=make_backends(Counter()))
    assert (r2.run_dir / "work" / "audio_16k_mono.wav").exists()


def test_geen_token_in_de_uitvoer(setup, monkeypatch):
    monkeypatch.setenv("HF_TOKEN", "hf_GEHEIM_TESTWAARDE_123")
    audio, settings = setup
    r = run_pipeline(audio, settings, backends=make_backends(Counter()))
    for f in r.run_dir.rglob("*.json"):
        assert "GEHEIM_TESTWAARDE" not in f.read_text(encoding="utf-8")


def test_slechte_audio_maakt_geen_run_en_geeft_vriendelijke_fout(setup, tmp_path):
    _, settings = setup
    with pytest.raises(StudieStapError):
        run_pipeline(tmp_path / "bestaat_niet.mp3", settings, backends=make_backends(Counter()))
    assert not (tmp_path / "out").exists()


def test_reporter_krijgt_start_en_einde_van_elke_stap(setup):
    audio, settings = setup

    class Rec(Reporter):
        def __init__(self):
            self.started, self.done = [], []
        def on_start(self, name, description): self.started.append(name)
        def on_done(self, record): self.done.append((record.name, record.status))

    rep = Rec()
    run_pipeline(audio, settings, backends=make_backends(Counter()), reporter=rep)
    assert rep.started == [n for n, _ in rep.done]
    assert rep.started[0] == "transcription" and "quality" in rep.started


def test_stemconsistentie_staat_standaard_uit_en_laat_labels_ongemoeid_als_ze_aan_staat(setup):
    from studiestap.models import SegmentVoiceCheck
    audio, settings = setup
    r = run_pipeline(audio, settings, backends=make_backends(Counter()))
    assert "voice_consistency" not in {s.name for s in r.steps} and "voice_consistency" not in load(r, "07_result.json")

    be = make_backends(Counter())
    be.voice_check = lambda sp, d, wav, s: [SegmentVoiceCheck(0, "SPEAKER_00", "CLOSER_TO_OTHER_SPEAKER", "t", 0.1,
                                                              "SPEAKER_01", 0.6, 0.4)]
    settings.voice_consistency.enabled = True
    r2 = run_pipeline(audio, settings, backends=be, force=True)
    res = load(r2, "07_result.json")
    assert (r2.run_dir / "05b_voice_consistency.json").exists()
    assert "VOICE_CLOSER_TO_OTHER_SPEAKER" in res["segments"][0]["quality"]["signals"][-1]["code"]
    assert load(r2, "02_diarization_raw.json")["intervals"] == load(r, "02_diarization_raw.json")["intervals"]
    assert [s["text"] for s in res["segments"]] == ["welkom allemaal", "vragen jullie dat"]
