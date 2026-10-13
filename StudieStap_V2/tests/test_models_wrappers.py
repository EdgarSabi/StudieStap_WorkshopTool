"""Mijlpaal B: dunne omhulsels om de modellen (transcriptie, diarizatie, woorduitlijning).

Integratietests met nep-modellen. Ze bewijzen dat onze code de uitvoer van een model
correct overneemt en fouten netjes afhandelt - NIET dat de echte modellen nauwkeurig zijn.
"""
from types import SimpleNamespace

import pytest

from studiestap.alignment import words as words_module
from studiestap.alignment.words import align_words
from studiestap.diarization.pyannote import PyannoteDiarizer, get_diarizer
from studiestap.models import Segment, StepStatus, StudieStapError, Transcript
from studiestap.settings import AlignmentSettings, DiarizationSettings, TranscriptionSettings
from studiestap.transcription.whisper import transcribe


# ------------------------------------------------------------ transcriptie
class FakeWhisper:
    def __init__(self, segments, fail=False):
        self.segments, self.fail, self.kwargs = segments, fail, None

    def transcribe(self, path, **kwargs):
        self.kwargs = kwargs
        if self.fail:
            raise RuntimeError("geheugen op")
        return iter(self.segments), SimpleNamespace(duration=12.5)


def test_transcriptie_neemt_segmenten_en_ruwe_signalen_over():
    raw = [SimpleNamespace(start=0.0, end=2.0, text="  hallo  ", avg_logprob=-0.3, no_speech_prob=0.01,
                           compression_ratio=1.2),
           SimpleNamespace(start=2.0, end=3.0, text="", avg_logprob=-2.0, no_speech_prob=0.9,
                           compression_ratio=3.0)]
    model = FakeWhisper(raw)
    t = transcribe("x.wav", TranscriptionSettings(), model_factory=lambda s: model)
    assert [s.id for s in t.segments] == [0, 1]
    assert t.segments[0].text == "hallo"
    assert t.segments[1].text == "" and t.segments[1].avg_logprob == -2.0   # lege tekst blijft zichtbaar
    assert t.duration_seconds == 12.5 and t.model == "faster-whisper/medium"
    assert model.kwargs["language"] == "nl" and model.kwargs["beam_size"] == 5


def test_transcriptiefout_wordt_vriendelijke_fout():
    with pytest.raises(StudieStapError) as e:
        transcribe("x.wav", TranscriptionSettings(), model_factory=lambda s: FakeWhisper([], fail=True))
    assert "Transcriberen is mislukt" in e.value.message and e.value.hint


# ------------------------------------------------------------ diarizatie
class FakeAnnotation:
    def __init__(self, rows):
        self.rows = rows

    def itertracks(self, yield_label=True):
        for s, e, label in self.rows:
            yield SimpleNamespace(start=s, end=e), None, label


ROWS = [(5.0, 6.0, "SPEAKER_01"), (0.0, 4.0, "SPEAKER_00"), (3.0, 5.0, "SPEAKER_01")]  # overlap 3-4


@pytest.mark.parametrize("vorm", ["pyannote4", "pyannote3"])
def test_diarizatie_behoudt_overlappende_ruwe_intervallen(vorm):
    ann = FakeAnnotation(ROWS)
    output = SimpleNamespace(speaker_diarization=ann) if vorm == "pyannote4" else ann
    d = PyannoteDiarizer(DiarizationSettings(), pipeline=object())._to_result(output, 1.0)
    got = [(i.speaker, i.start, i.end) for i in d.intervals]
    assert len(got) == 3                                               # niets weggegooid
    assert ("SPEAKER_00", 0.0, 4.0) in got and ("SPEAKER_01", 3.0, 5.0) in got   # overlap 3-4 blijft
    assert got == sorted(got, key=lambda r: (r[1], r[2], r[0]))
    assert d.backend == "pyannote"


def test_onbekende_diarizatiebackend():
    with pytest.raises(StudieStapError):
        get_diarizer(DiarizationSettings(backend="bestaatniet"))


# ------------------------------------------------------------ woorduitlijning
def transcript():
    return Transcript("nl", 6.0, "m", {}, 0.0, [Segment(0, 0, 2, "dit is een test"), Segment(1, 2, 4, "tweede zin")])


def fake_aligner(segments, wav):
    return [{"start": s["start"], "end": s["end"],
             "words": [{"word": w, "start": s["start"] + 0.1 * i, "end": s["start"] + 0.1 * i + 0.05, "score": 0.9}
                       for i, w in enumerate(s["text"].split())]} for s in segments]


def test_alignment_geslaagd_bij_volledige_woordtijden():
    a = align_words(transcript(), "x.wav", AlignmentSettings(), aligner=fake_aligner)
    assert a.status == StepStatus.SUCCEEDED and len(a.segments[0].words) == 4


def test_alignment_gedeeltelijk_als_een_woord_geen_tijd_heeft():
    def aligner(segs, wav):
        out = fake_aligner(segs, wav)
        out[0]["words"][1] = {"word": "is"}   # zonder start/eind
        return out
    a = align_words(transcript(), "x.wav", AlignmentSettings(), aligner=aligner)
    assert a.status == StepStatus.PARTIAL and a.segments[0].status == StepStatus.PARTIAL
    assert a.segments[1].status == StepStatus.SUCCEEDED
    assert a.segments[0].words[1].start is None   # niets bijgevuld


def test_alignment_mislukt_bij_crash_en_bij_segment_buiten_alle_invoer():
    def crash(segs, wav):
        raise RuntimeError("boem")
    assert align_words(transcript(), "x.wav", AlignmentSettings(), aligner=crash).status == StepStatus.FAILED
    buiten = align_words(transcript(), "x.wav", AlignmentSettings(),
                         aligner=lambda s, w: [{"start": 50.0, "end": 51.0, "words": [{"word": "x", "start": 50, "end": 51}]}])
    assert buiten.status == StepStatus.FAILED and buiten.segments == []


def test_whisperx_zinssplitsing_wordt_teruggekoppeld_aan_het_juiste_invoersegment():
    # WhisperX gaf in de echte run 90 segmenten voor 87 invoersegmenten. Verwacht: woorden van beide
    # deelzinnen horen bij segment 0; segment 1 blijft ongemoeid.
    def aligner(segs, wav):
        return [{"start": 0.0, "end": 0.9, "words": [{"word": "dit", "start": 0.0, "end": 0.4}]},
                {"start": 1.0, "end": 1.9, "words": [{"word": "is", "start": 1.0, "end": 1.4}]},
                {"start": 2.0, "end": 3.9, "words": [{"word": "tweede", "start": 2.1, "end": 3.0}]}]
    a = align_words(transcript(), "x.wav", AlignmentSettings(), aligner=aligner)
    assert [w.text for w in a.segments[0].words] == ["dit", "is"]
    assert [w.text for w in a.segments[1].words] == ["tweede"]
    assert a.status == StepStatus.SUCCEEDED


def test_segment_zonder_uitgelijnde_woorden_maakt_alignment_gedeeltelijk():
    a = align_words(transcript(), "x.wav", AlignmentSettings(), aligner=lambda s, w: fake_aligner(s, w)[:1] and
                    [{"start": 0.0, "end": 2.0, "words": [{"word": "dit", "start": 0.0, "end": 0.4}]}])
    assert a.status == StepStatus.PARTIAL and a.segments[1].status == StepStatus.FAILED


def test_alignment_niet_beschikbaar_zonder_whisperx(monkeypatch):
    monkeypatch.setattr(words_module, "whisperx_installed", lambda: False)
    a = align_words(transcript(), "x.wav", AlignmentSettings())
    assert a.status == StepStatus.UNAVAILABLE and "segmentniveau" in a.message
    assert a.segments == []


def test_alignment_wordt_aangeroepen_met_bestaande_segmenten_zonder_nieuwe_transcriptie():
    gezien = {}
    def aligner(segs, wav):
        gezien["segs"] = segs
        return fake_aligner(segs, wav)
    align_words(transcript(), "x.wav", AlignmentSettings(), aligner=aligner)
    assert gezien["segs"] == [{"start": 0, "end": 2, "text": "dit is een test"},
                              {"start": 2, "end": 4, "text": "tweede zin"}]
