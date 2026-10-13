"""De pipeline: knoopt de losse modules aan elkaar. Hier zit zelf bijna geen logica.

Volgorde van `analyze`:
  audio voorbereiden -> transcriberen -> diarizatie -> woorduitlijning
  -> sprekerkoppeling -> docentherkenning -> (optioneel: stemconsistentie) -> kwaliteit -> classificatie -> eindresultaat

Spelregels:
  * Een stap die faalt of niet beschikbaar is, stopt de rest NIET (behalve transcriptie:
    zonder tekst valt er niets te analyseren). De status staat in run_manifest.json.
  * Dure modelstappen worden niet herhaald als audio + instellingen gelijk zijn
    (zie `_try_cache`). Gebruik force=True om opnieuw te draaien.
  * Ruwe uitvoer (01-03) wordt nooit aangepast door latere stappen.
"""
from __future__ import annotations

import hashlib
import json
import platform
import re
import shutil
import time
from dataclasses import dataclass, field
from importlib import metadata
from pathlib import Path
from typing import Callable, Optional

from . import __version__
from .alignment.speakers import couple_speakers
from .alignment.words import align_words
from .audio.loader import prepare_audio, sha256_of_file, validate_audio_path
from .classification.base import ConversationContext, Utterance
from .classification.indicators import run_indicators
from .models import (AlignedSegment, AudioInfo, Diarization, QualityReport, Segment, SegmentSpeakers,
                     SegmentVoiceCheck, SpeakerInterval, SpeakerRole, StepRecord, StepStatus, StudieStapError, Transcript,
                     Word, WordAlignment, to_dict)
from .output.exporter import MANIFEST_NAME, read_json, write_json
from .quality.checks import build_quality_report
from .recognition.teacher import (build_clip_embedder, build_wespeaker_embedder, no_reference_roles,
                                  recognize_teacher)
from .recognition.voice_consistency import check_voice_consistency
from .settings import Settings, apply_offline_mode
from .transcription.whisper import transcribe

FILES = {
    "transcription": "01_transcript.json",
    "diarization": "02_diarization_raw.json",
    "word_alignment": "03_word_alignment.json",
    "speaker_assignment": "04_speaker_assignment.json",
    "teacher_roles": "05_teacher_roles.json",
    "voice_consistency": "05b_voice_consistency.json",
    "quality": "06_quality.json",
    "result": "07_result.json",
}
SCHEMA_VERSION = "1.0"


# ------------------------------------------------------------------ terugvallen op echte modules

def _default_diarize(wav: Path, settings: Settings) -> Diarization:
    from .diarization.pyannote import get_diarizer
    return get_diarizer(settings.diarization).diarize(wav)


def _default_recognize(diarization: Diarization, wav: Path, reference_wav: Path, settings: Settings):
    reference, embed_clip = build_wespeaker_embedder(str(wav), str(reference_wav), settings.teacher_recognition)
    return recognize_teacher(diarization.intervals, reference, embed_clip, settings.teacher_recognition)


def _default_voice_check(speakers: list[SegmentSpeakers], diarization: Diarization, wav: Path, settings: Settings):
    embed_clip = build_clip_embedder(str(wav), settings.teacher_recognition)
    return check_voice_consistency(speakers, diarization.intervals, embed_clip,
                                   settings.teacher_recognition.min_clip_seconds)


@dataclass
class Backends:
    """De zware stappen als functies. Tests geven hier nep-versies; normaal blijft het zoals het is."""
    transcribe: Callable[[Path, Settings], Transcript] = lambda wav, s: transcribe(wav, s.transcription)
    diarize: Callable[[Path, Settings], Diarization] = _default_diarize
    align: Callable[[Transcript, Path, Settings], WordAlignment] = \
        lambda t, wav, s: align_words(t, wav, s.alignment)
    recognize: Callable[..., list[SpeakerRole]] = _default_recognize
    voice_check: Callable[..., list[SegmentVoiceCheck]] = _default_voice_check


class Reporter:
    """Meldt voortgang. De CLI erft hiervan en print; standaard doet het niets."""
    def on_start(self, name: str, description: str) -> None: ...
    def on_done(self, record: StepRecord) -> None: ...


@dataclass
class RunReport:
    run_dir: Path
    ok: bool
    steps: list[StepRecord] = field(default_factory=list)
    result_path: Optional[Path] = None


# ------------------------------------------------------------------ van JSON terug naar objecten (voor cache)

def _transcript_from_dict(d: dict) -> Transcript:
    return Transcript(**{**d, "segments": [Segment(**s) for s in d["segments"]]})


def _diarization_from_dict(d: dict) -> Diarization:
    return Diarization(**{**d, "intervals": [SpeakerInterval(**i) for i in d["intervals"]]})


def _alignment_from_dict(d: dict) -> WordAlignment:
    segs = [AlignedSegment(segment_id=s["segment_id"], status=StepStatus(s["status"]),
                           words=[Word(**w) for w in s["words"]]) for s in d["segments"]]
    return WordAlignment(**{**d, "status": StepStatus(d["status"]), "segments": segs})


_LOADERS = {"transcription": _transcript_from_dict, "diarization": _diarization_from_dict,
            "word_alignment": _alignment_from_dict}


# ------------------------------------------------------------------ hulpfuncties

def _fingerprint(*parts) -> str:
    return hashlib.sha256(json.dumps(parts, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def _safe_stem(path: Path) -> str:
    return re.sub(r"[^\w.-]+", "_", path.stem)[:40] or "audio"


def _package_versions() -> dict:
    out = {"studiestap": __version__, "python": platform.python_version()}
    for pkg in ("faster-whisper", "pyannote.audio", "whisperx", "torch", "ctranslate2"):
        try:
            out[pkg] = metadata.version(pkg)
        except metadata.PackageNotFoundError:
            out[pkg] = None
    return out


class _Run:
    """Houdt per run bij: map, vorige manifest, stappen en bestandshashes."""

    def __init__(self, run_dir: Path, audio: AudioInfo, settings: Settings, force: bool,
                 reporter: Reporter, debug: bool):
        self.dir, self.audio, self.settings = run_dir, audio, settings
        self.force, self.reporter, self.debug = force, reporter, debug
        self.records: list[StepRecord] = []
        self.manifest_steps: dict[str, dict] = {}
        self.prev_steps: dict[str, dict] = {}
        prev_path = run_dir / MANIFEST_NAME
        if prev_path.exists():
            try:
                self.prev_steps = read_json(prev_path).get("steps", {})
            except (json.JSONDecodeError, OSError):
                self.prev_steps = {}

    def execute(self, name: str, description: str, fn: Callable[[], tuple], *,
                fingerprint: Optional[str] = None, save: bool = True):
        """Draai een stap. `fn` geeft (object, status, bericht) terug. Fouten worden een FAILED-record."""
        self.reporter.on_start(name, description)
        started = time.time()
        reused = False
        value = None
        try:
            cached = self._try_cache(name, fingerprint)
            if cached is not None:
                value, status, message = cached
                reused = True
            else:
                value, status, message = fn()
        except StudieStapError as e:
            status, message = StepStatus.FAILED, e.message + (f" Tip: {e.hint}" if e.hint else "")
        except Exception as e:  # onverwacht: toch netjes vastleggen
            if self.debug:
                raise
            status, message = StepStatus.FAILED, f"Onverwachte fout ({type(e).__name__}: {e}). Gebruik --debug voor details."

        out_file, digest = None, None
        if value is not None and save and name in FILES:
            out_file = FILES[name]
            if not reused:
                digest = write_json(self.dir / out_file, value)
            else:
                digest = self.prev_steps[name].get("sha256")
        record = StepRecord(name=name, status=status, message=message, output_file=out_file,
                            runtime_seconds=round(time.time() - started, 2), reused_from_cache=reused)
        self.records.append(record)
        self.manifest_steps[name] = {**to_dict(record), "sha256": digest, "fingerprint": fingerprint}
        self.reporter.on_done(record)
        return value, record

    def _try_cache(self, name: str, fingerprint: Optional[str]):
        prev = self.prev_steps.get(name)
        if self.force or fingerprint is None or not prev or name not in _LOADERS:
            return None
        if prev.get("fingerprint") != fingerprint or prev.get("status") not in ("succeeded", "partial"):
            return None
        path = self.dir / prev.get("output_file", "")
        if not path.is_file():
            return None
        try:
            return _LOADERS[name](read_json(path)), StepStatus(prev["status"]), prev.get("message", "")
        except (json.JSONDecodeError, TypeError, KeyError):
            return None  # kapotte cache: gewoon opnieuw rekenen

    def write_manifest(self, extra: dict) -> None:
        write_json(self.dir / MANIFEST_NAME, {
            "schema_version": SCHEMA_VERSION,
            "audio": {k: v for k, v in to_dict(self.audio).items() if k != "working_wav"},
            "settings": self.settings.to_dict(),
            "versions": _package_versions(),
            "steps": self.manifest_steps,
            **extra,
        })


# ------------------------------------------------------------------ de pipeline zelf

def run_pipeline(
    audio_path: str | Path,
    settings: Settings,
    *,
    mode: str = "analyze",                    # "transcribe" of "analyze"
    teacher_reference: Optional[str | Path] = None,
    force: bool = False,
    skip_alignment: bool = False,
    backends: Optional[Backends] = None,
    reporter: Optional[Reporter] = None,
    debug: bool = False,
) -> RunReport:
    backends = backends or Backends()
    reporter = reporter or Reporter()
    apply_offline_mode(settings)

    out_root = Path(settings.output.directory)
    # De sha256 bepaalt de runmap: dezelfde opname -> dezelfde map -> hergebruik van resultaten.
    probe = validate_audio_path(audio_path)   # StudieStapError bij een slecht bestand: geen run aangemaakt
    run_dir = out_root / f"{_safe_stem(probe)}_{sha256_of_file(probe)[:8]}"
    work_dir = run_dir / "work"
    audio = prepare_audio(probe, work_dir)

    run = _Run(run_dir, audio, settings, force, reporter, debug)
    wav = Path(audio.working_wav)
    ts = settings.transcription.__dict__
    try:
        # 1. transcriptie ------------------------------------------------
        transcript, rec = run.execute(
            "transcription", "Spraak omzetten naar tekst (faster-whisper)",
            lambda: _ok(backends.transcribe(wav, settings), "Transcriptie klaar."),
            fingerprint=_fingerprint("transcription", audio.sha256, ts))
        if rec.status == StepStatus.FAILED:
            run.write_manifest({"overall": "failed"})
            return RunReport(run_dir, False, run.records)
        if mode == "transcribe":
            run.write_manifest({"overall": "ok"})
            return RunReport(run_dir, True, run.records, run_dir / FILES["transcription"])

        # 2. diarizatie --------------------------------------------------
        diarization, rec = run.execute(
            "diarization", "Sprekers detecteren (pyannote)",
            lambda: _ok(backends.diarize(wav, settings), "Diarizatie klaar."),
            fingerprint=_fingerprint("diarization", audio.sha256, settings.diarization.__dict__))
        if rec.status == StepStatus.FAILED:
            diarization = None

        # 3. woorduitlijning (op de bestaande transcriptie, geen tweede transcriptie) ----
        if skip_alignment or not settings.alignment.enabled:
            alignment, _ = run.execute(
                "word_alignment", "Woorduitlijning", lambda: (None, StepStatus.SKIPPED, "Uitgeschakeld."))
        else:
            def do_align():
                a = backends.align(transcript, wav, settings)
                return a, a.status, a.message
            alignment, _ = run.execute(
                "word_alignment", "Woorden uitlijnen (WhisperX)", do_align,
                fingerprint=_fingerprint("align", audio.sha256, ts, settings.alignment.__dict__))

        # 4. sprekerkoppeling -------------------------------------------
        speakers = None
        if diarization is not None:
            speakers, _ = run.execute(
                "speaker_assignment", "Sprekers aan segmenten en woorden koppelen",
                lambda: _ok(couple_speakers(transcript.segments, diarization.intervals, alignment,
                                            settings.speakers.min_single_speaker_coverage),
                            "Alle intersecties bewaard."))
        else:
            run.execute("speaker_assignment", "Sprekers koppelen",
                        lambda: (None, StepStatus.UNAVAILABLE, "Geen diarizatie beschikbaar."))

        # 5. docentherkenning ------------------------------------------
        roles = _teacher_step(run, backends, diarization, wav, teacher_reference, work_dir)

        # 5b. stemconsistentie (optioneel, alleen diagnostiek) ---------------
        voice_checks = None
        if settings.voice_consistency.enabled and speakers is not None:
            voice_checks, _ = run.execute(
                "voice_consistency", "Stem per segment vergelijken met het sprekerlabel (WeSpeaker)",
                lambda: _ok(backends.voice_check(speakers, diarization, wav, settings),
                            "Diagnostiek klaar; labels zijn niet aangepast."))

        # 6. kwaliteit -------------------------------------------------
        quality, _ = run.execute(
            "quality", "Kwaliteitssignalen verzamelen",
            lambda: _ok(build_quality_report(transcript, speakers, alignment, roles, settings.quality, voice_checks),
                        "Signalen verzameld (waarnemingen, geen oordeel)."))

        # 7. classificatie + eindresultaat ------------------------------
        result = _assemble_result(run, transcript, diarization, alignment, speakers, roles, quality, voice_checks)
        result["steps"] = {k: {kk: vv for kk, vv in v.items() if kk != "fingerprint"}
                           for k, v in run.manifest_steps.items()}
        result["steps"]["classification"] = {"status": result["classification"]["status"].lower()}
        digest = write_json(run.dir / FILES["result"], result)
        run.manifest_steps["result"] = {"name": "result", "status": "succeeded", "output_file": FILES["result"],
                                        "sha256": digest, "message": "Samengevoegd eindresultaat."}
        run.write_manifest({"overall": "ok"})
        return RunReport(run_dir, True, run.records, run_dir / FILES["result"])
    finally:
        if not settings.output.keep_audio:
            shutil.rmtree(work_dir, ignore_errors=True)  # privacy: geen audiokopie laten staan


def _ok(value, message: str):
    return value, StepStatus.SUCCEEDED, message


def _teacher_step(run: _Run, backends: Backends, diarization: Optional[Diarization], wav: Path,
                  reference: Optional[str | Path], work_dir: Path) -> Optional[list[SpeakerRole]]:
    if diarization is None:
        run.execute("teacher_roles", "Docentherkenning",
                    lambda: (None, StepStatus.UNAVAILABLE, "Geen diarizatie, dus geen sprekers om te herkennen."))
        return None
    if reference is None:
        roles, _ = run.execute(
            "teacher_roles", "Docentherkenning",
            lambda: (no_reference_roles(diarization.intervals), StepStatus.SKIPPED,
                     "Geen referentieopname opgegeven (--teacher-reference): docentidentiteit onbekend."))
        return roles

    def do():
        ref = prepare_audio(reference, work_dir / "reference")
        roles = backends.recognize(diarization, wav, Path(ref.working_wav), run.settings)
        return roles, StepStatus.SUCCEEDED, f"Vergeleken met referentie (sha256 {ref.sha256[:8]})."
    roles, rec = run.execute("teacher_roles", "Docent herkennen met WeSpeaker", do)
    if rec.status == StepStatus.FAILED:
        # Niet kunnen herkennen is onbekend, geen bewijs voor iets.
        return [SpeakerRole(s, "UNKNOWN", "onbekend", note="Docentherkenning mislukt.")
                for s in sorted({i.speaker for i in diarization.intervals})]
    return roles


def _assemble_result(run: _Run, transcript: Transcript, diarization: Optional[Diarization],
                     alignment: Optional[WordAlignment], speakers: Optional[list[SegmentSpeakers]],
                     roles: Optional[list[SpeakerRole]], quality: Optional[QualityReport],
                     voice_checks: Optional[list[SegmentVoiceCheck]] = None) -> dict:
    sp_by_id = {s.segment_id: s for s in (speakers or [])}
    q_by_id = {q.segment_id: q for q in (quality.segments if quality else [])}
    role_by_speaker = {r.speaker: r.role for r in (roles or [])}

    segments, utterances = [], []
    for seg in transcript.segments:
        sp, q = sp_by_id.get(seg.id), q_by_id.get(seg.id)
        segments.append({
            "id": seg.id, "start": seg.start, "end": seg.end,
            "text": seg.text,   # tekst blijft altijd behouden, ook bij onzekere rol
            "asr": {"avg_logprob": seg.avg_logprob, "no_speech_prob": seg.no_speech_prob,
                    "compression_ratio": seg.compression_ratio},
            "speakers": to_dict(sp) if sp else None,
            "quality": to_dict(q) if q else None,
        })
        names = sorted(sp.seconds_per_speaker) if sp else []
        utterances.append(Utterance(
            segment_id=seg.id, start=seg.start, end=seg.end, text=seg.text, speakers=names,
            roles=sorted({role_by_speaker.get(n, "onbekend") for n in names}),
            review_status=q.status.value if q else "REVIEW_REQUIRED",
            signals=[s.code for s in q.signals] if q else []))

    classification = run_indicators(ConversationContext(utterances, language=transcript.language))
    return {
        "schema_version": SCHEMA_VERSION,
        "audio": {k: v for k, v in to_dict(run.audio).items() if k != "working_wav"},
        "language": transcript.language,
        "raw_speakers": sorted({i.speaker for i in diarization.intervals}) if diarization else [],
        "speaker_roles": to_dict(roles) if roles is not None else None,
        "segments": segments,
        **({"voice_consistency": to_dict(voice_checks)} if voice_checks is not None else {}),  # alleen als aan
        "quality": {"note": quality.note, "global_signals": to_dict(quality.global_signals)} if quality else None,
        "classification": to_dict(classification),
        "provenance": {
            "versions": _package_versions(),
            "settings": run.settings.to_dict(),
            "parts": {k: {"file": FILES[k], "sha256": v.get("sha256")}
                      for k, v in run.manifest_steps.items() if k in FILES and v.get("sha256")},
            "note": "Elk deelbestand is los bewaard; de sha256 hoort bij de inhoud van dat bestand.",
        },
    }
