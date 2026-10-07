"""
STAP 2 — Speaker diarization: Wie spreekt wanneer. Hier worden nog geen labels aan de personen toegevoegd (zoals docent of andere spreker)
Dit gebeurt in een vervolgstap

Draaien:
    python diarization.py --transcript <Phase 1 JSON> [--audio ...] [--min-speakers N] [--max-speakers N] [--force]

Uses pyannote.audio (the only ML model in this file) to find raw speaker
turns ("SPEAKER_00 talked from 3.2s to 7.1s"), then:
  1. build_label_map()   turns those raw ids into MAIN_SPEAKER / OTHER_SPEAKER_n,
                          based on who talked the most overall.
  2. assign_speakers()   couples each transcript TEXT segment to whichever
                          speaker's turn overlaps it the most in time.
Both steps are pure arithmetic on start/end times — no ML, easy to read on
their own even without understanding pyannote.

Setup (one-time, done by a human — gated model + credentials):
  1. pip install pyannote.audio
  2. On huggingface.co accept the user conditions for BOTH
       pyannote/speaker-diarization-3.1
       pyannote/segmentation-3.0
  3. Create a read token and put it in <repo-root>/.env as:  HF_TOKEN=hf_xxx
"""
import argparse
import json
import shutil
import subprocess
import sys
import time
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from config import DiarizationConfig, DIARIZATION_OUTPUT_DIR, RAW_DATA_DIR, TEST_FILES_DIR, get_hf_token
from models import TranscriptSegment, WorkshopTranscript

MAIN_SPEAKER = "MAIN_SPEAKER"

@dataclass
class SpeakerTurn:
    """One contiguous stretch attributed to a single speaker, in seconds.
    `speaker` is pyannote's own raw label (e.g. "SPEAKER_00") — mapping that
    to MAIN_SPEAKER / OTHER_SPEAKER_n happens in build_label_map() below."""
    start: float
    end: float
    speaker: str
    confidence: Optional[float] = None

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)


@dataclass
class DiarizationResult:
    turns: list[SpeakerTurn]
    backend: str
    model: str
    settings: dict = field(default_factory=dict)
    runtime_seconds: float = 0.0

    @property
    def raw_speakers(self) -> list[str]:
        return sorted({t.speaker for t in self.turns})

    def talk_time(self) -> dict[str, float]:
        """Total speaking seconds per raw speaker label."""
        totals: dict[str, float] = {}
        for t in self.turns:
            totals[t.speaker] = totals.get(t.speaker, 0.0) + t.duration
        return totals


# ============================================================
# pyannote.audio — the only ML model in this file
# ============================================================

def _load_wav_waveform(wav_path: Path):
    """Read a 16-bit PCM WAV into a (channels, samples) float32 torch tensor.

    We decode the audio ourselves and hand pyannote a waveform, instead of a
    file path, so pyannote never calls torchcodec. torchcodec on Windows needs
    FFmpeg *shared* DLLs; a static ffmpeg.exe (what's on this machine) is not
    enough. to_wav() below already produced this 16 kHz mono WAV with the
    ffmpeg CLI, so no decoding library is needed here.
    """
    import numpy as np
    import torch

    with wave.open(str(wav_path), "rb") as w:
        if w.getcomptype() != "NONE":
            raise RuntimeError(f"{wav_path.name} is compressed WAV; expected 16-bit PCM.")
        if w.getsampwidth() != 2:
            raise RuntimeError(
                f"{wav_path.name} has {w.getsampwidth() * 8}-bit samples; "
                f"to_wav() should produce 16-bit PCM."
            )
        n_channels = w.getnchannels()
        sample_rate = w.getframerate()
        raw = w.readframes(w.getnframes())

    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    if n_channels > 1:
        samples = samples.reshape(-1, n_channels).T          # (channels, samples)
    else:
        samples = samples[np.newaxis, :]                       # (1, samples)
    return torch.from_numpy(np.ascontiguousarray(samples)), sample_rate


# A class because loading the pyannote model (Pipeline.from_pretrained) is
# slow — you load it ONCE in __init__, then call .diarize() as many times as
# you have fragments to process, reusing the same loaded model each time.
class PyannoteBackend:
    name = "pyannote"

    def __init__(self, config: DiarizationConfig):
        self.config = config

        try:
            import torch
            from pyannote.audio import Pipeline
        except ImportError as e:
            raise ImportError(
                "pyannote.audio is not installed. Run:  pip install pyannote.audio"
            ) from e

        token = get_hf_token()
        if not token:
            raise RuntimeError(
                "No HuggingFace token found. Put HF_TOKEN=... in <repo-root>/.env "
                "(see this file's docstring for the full setup)."
            )

        try:
            # pyannote.audio >= 3.3 renamed use_auth_token -> token; keep both working.
            try:
                self._pipeline = Pipeline.from_pretrained(config.hf_model, token=token)
            except TypeError:
                self._pipeline = Pipeline.from_pretrained(config.hf_model, use_auth_token=token)
        except Exception as e:
            raise RuntimeError(
                f"Could not load '{config.hf_model}'. If this is a 401/403 or mentions "
                f"access/gated: accept the user conditions for BOTH "
                f"pyannote/speaker-diarization-3.1 AND pyannote/segmentation-3.0 on "
                f"huggingface.co with the account this token belongs to. "
                f"Original error: {e}"
            ) from e

        if self._pipeline is None:
            # from_pretrained returns None (not raises) on an auth/licence problem
            raise RuntimeError(
                f"Pipeline.from_pretrained('{config.hf_model}') returned None — this "
                f"means the token is invalid or the model licence has not been accepted."
            )

        self._pipeline.to(torch.device(config.device))
        self._apply_clustering_overrides()

    def _apply_clustering_overrides(self) -> None:
        """Optioneel min_cluster_size / threshold van pyannote's clustering
        overschrijven (zelfde manier als het hyperparameter-experiment)."""
        overrides = {}
        if self.config.clustering_min_cluster_size is not None:
            overrides["min_cluster_size"] = int(self.config.clustering_min_cluster_size)
        if self.config.clustering_threshold is not None:
            overrides["threshold"] = float(self.config.clustering_threshold)
        if not overrides:
            return
        params = json.loads(json.dumps(self._pipeline.parameters(instantiated=True)))
        params.setdefault("clustering", {}).update(overrides)
        self._pipeline.instantiate(params)

    def diarize(
        self,
        audio_path: Path,
        *,
        min_speakers: Optional[int] = None,
        max_speakers: Optional[int] = None,
    ) -> DiarizationResult:
        kwargs = {}
        if min_speakers is not None:
            kwargs["min_speakers"] = min_speakers
        if max_speakers is not None:
            kwargs["max_speakers"] = max_speakers

        waveform, sample_rate = _load_wav_waveform(Path(audio_path))

        start = time.time()
        output = self._pipeline({"waveform": waveform, "sample_rate": sample_rate}, **kwargs)
        runtime = time.time() - start

        # pyannote 4.x returns a DiarizeOutput (with .speaker_diarization);
        # pyannote 3.x returns the Annotation directly.
        annotation = getattr(output, "speaker_diarization", output)

        turns = [
            SpeakerTurn(start=float(segment.start), end=float(segment.end), speaker=str(label))
            for segment, _track, label in annotation.itertracks(yield_label=True)
        ]
        turns.sort(key=lambda t: (t.start, t.end))

        return DiarizationResult(
            turns=turns,
            backend=self.name,
            model=self.config.hf_model,
            settings={
                "device": self.config.device,
                "min_speakers": min_speakers,
                "max_speakers": max_speakers,
                "clustering_min_cluster_size": self.config.clustering_min_cluster_size,
                "clustering_threshold": self.config.clustering_threshold,
            },
            runtime_seconds=round(runtime, 2),
        )


# ============================================================
# Turning raw "SPEAKER_00"/"SPEAKER_01" labels into MAIN_SPEAKER/OTHER_SPEAKER_n
# ============================================================

def build_label_map(result: DiarizationResult, *, main_speaker_min_share: float = 0.0) -> dict:
    """Heuristic for classroom recordings: whoever talks the most overall
    becomes MAIN_SPEAKER, everyone else becomes OTHER_SPEAKER_1, _2, ... by
    talk time. This is NOT speaker identification and makes no claim about
    who any OTHER_SPEAKER is — see docent_recognition.py for actual voice
    recognition against a reference recording.

    Returns {raw_label: friendly_label} plus a small inventory for the report:
      {
        "map": {"SPEAKER_00": "MAIN_SPEAKER", "SPEAKER_01": "OTHER_SPEAKER_1", ...},
        "inventory": [{"raw": "SPEAKER_00", "label": "MAIN_SPEAKER", "talk_seconds": 61.2, "share": 0.74}, ...],
        "main_speaker_uncertain": False,
      }
    """
    talk = result.talk_time()
    total = sum(talk.values())
    ranked = sorted(talk.items(), key=lambda kv: kv[1], reverse=True)

    label_map: dict[str, str] = {}
    inventory = []
    for i, (raw, seconds) in enumerate(ranked):
        friendly = MAIN_SPEAKER if i == 0 else f"OTHER_SPEAKER_{i}"
        label_map[raw] = friendly
        inventory.append(
            {
                "raw": raw,
                "label": friendly,
                "talk_seconds": round(seconds, 2),
                "share": round(seconds / total, 4) if total else 0.0,
            }
        )

    main_share = ranked[0][1] / total if (ranked and total) else 0.0
    return {
        "map": label_map,
        "inventory": inventory,
        "main_speaker_uncertain": main_share < main_speaker_min_share,
    }


# ============================================================
# Coupling speaker turns onto transcript text segments
# ============================================================
# Pure time-span geometry — no model, no I/O. Given a transcript segment's
# [start, end] and the list of speaker turns, decide:
#   - which speaker "owns" the segment (most overlapping time)
#   - a confidence (owner's share of the segment's total attributed speech time)
#   - whether another speaker also covers a meaningful slice  -> overlap
#   - whether the assignment is shaky (low coverage or near-tie) -> uncertain
#
# Important: a segment with NO overlapping speaker turn is marked
# `uncertain_assignment=True` with `speaker=None`. That means "diarization did
# not attribute this speech", NOT "no one spoke".

def _overlap_seconds(a0: float, a1: float, b0: float, b1: float) -> float:
    return max(0.0, min(a1, b1) - max(a0, b0))


def assign_speakers(
    segments: list[TranscriptSegment],
    turns: list[SpeakerTurn],
    label_map: dict,
    *,
    overlap_min_ratio: float = 0.15,
    uncertain_coverage_below: float = 0.60,
    uncertain_margin_below: float = 0.15,
    turn_confidence_below: Optional[float] = None,
) -> list[TranscriptSegment]:
    """Return a NEW list of segments with speaker fields filled in. Input untouched.

    turn_confidence_below: alleen relevant voor verfijnde beurten
    (speaker_boundaries.py zet SpeakerTurn.confidence). Is het tijdgewogen
    stembewijs van de winnende spreker binnen dit segment lager dan deze
    waarde, dan wordt het segment uncertain_assignment — de refinement-stap
    twijfelde daar zelf ook. None = uit (oud gedrag)."""
    out: list[TranscriptSegment] = []

    for seg in segments:
        duration = max(0.0, seg.end - seg.start)

        per_speaker: dict[str, float] = {}
        conf_weighted: dict[str, list[float]] = {}  # [som(conf*overlap), som(overlap)]
        for t in turns:
            ov = _overlap_seconds(seg.start, seg.end, t.start, t.end)
            if ov > 0:
                per_speaker[t.speaker] = per_speaker.get(t.speaker, 0.0) + ov
                if t.confidence is not None:
                    acc = conf_weighted.setdefault(t.speaker, [0.0, 0.0])
                    acc[0] += t.confidence * ov
                    acc[1] += ov

        if not per_speaker or duration <= 0:
            out.append(seg.model_copy(update={
                "speaker": None,
                "speaker_raw": None,
                "speaker_confidence": None,
                "overlap": False,
                "uncertain_assignment": True,
            }))
            continue

        ranked = sorted(per_speaker.items(), key=lambda kv: kv[1], reverse=True)
        winner_raw, winner_ov = ranked[0]
        runner_ov = ranked[1][1] if len(ranked) > 1 else 0.0
        total_ov = sum(per_speaker.values())

        coverage = winner_ov / duration
        margin = (winner_ov - runner_ov) / duration
        confidence = winner_ov / total_ov if total_ov else 0.0

        low_evidence = False
        if turn_confidence_below is not None and winner_raw in conf_weighted:
            num, den = conf_weighted[winner_raw]
            low_evidence = den > 0 and (num / den) < turn_confidence_below

        out.append(seg.model_copy(update={
            "speaker": label_map.get(winner_raw, winner_raw),
            "speaker_raw": winner_raw,
            "speaker_confidence": round(confidence, 4),
            "overlap": (runner_ov / duration) >= overlap_min_ratio,
            "uncertain_assignment": (
                coverage < uncertain_coverage_below
                or margin < uncertain_margin_below
                or low_evidence
            ),
        }))

    return out


# ============================================================
# Stap 2b — sprekergrenzen verfijnen (zie speaker_boundaries.py)
# ============================================================

def refine_diarization(
    result: DiarizationResult,
    wav_path: Path,
    segments: list[TranscriptSegment],
    refine_config=None,
    embedder=None,
) -> tuple[DiarizationResult, dict]:
    """Verfijnt pyannote's beurten met stem-embeddings. Whisper-segmentgrenzen
    worden als kandidaat-wisselpunten meegegeven. Geeft een NIEUW
    DiarizationResult terug (origineel ongewijzigd) + metadata voor de JSON."""
    from config import BoundaryRefinementConfig
    from speaker_boundaries import PyannoteWindowEmbedder, refine_speaker_boundaries

    cfg = refine_config or BoundaryRefinementConfig()
    if embedder is None:
        embedder = PyannoteWindowEmbedder(cfg.embedding_model, device=cfg.device)

    waveform, sample_rate = _load_wav_waveform(Path(wav_path))
    samples = waveform.mean(dim=0).numpy() if waveform.shape[0] > 1 else waveform[0].numpy()

    asr_spans = [(s.start, s.end) for s in segments]

    t0 = time.time()
    refined = refine_speaker_boundaries(
        samples, sample_rate, result.turns, embedder, cfg,
        asr_spans=asr_spans,
    )
    runtime = round(time.time() - t0, 2)

    new_result = DiarizationResult(
        turns=refined.turns,
        backend=result.backend,
        model=result.model,
        settings=result.settings,
        runtime_seconds=result.runtime_seconds,
    )
    meta = refined.to_metadata()
    meta["runtime_seconds"] = runtime
    meta["embedding_model"] = cfg.embedding_model
    meta["config"] = {k: v for k, v in vars(cfg).items()}
    return new_result, meta


def summarize(segments: list[TranscriptSegment]) -> dict:
    """Counts for the CLI printout."""
    per_label: dict[str, int] = {}
    for s in segments:
        key = s.speaker or "UNASSIGNED"
        per_label[key] = per_label.get(key, 0) + 1
    return {
        "segments": len(segments),
        "per_label": per_label,
        "overlap_segments": sum(1 for s in segments if s.overlap),
        "uncertain_segments": sum(1 for s in segments if s.uncertain_assignment),
        "unassigned_segments": sum(1 for s in segments if s.speaker is None),
    }


# ============================================================
# CLI: Phase 1 transcript JSON -> diarized transcript JSON
# ============================================================

_WAV_SUFFIXES = {".wav"}


def _resolve_audio(transcript: WorkshopTranscript, audio_arg: str | None, dir_arg: str) -> Path:
    if audio_arg:
        base = TEST_FILES_DIR if dir_arg == "test" else RAW_DATA_DIR
        candidate = Path(audio_arg)
        return candidate if candidate.is_absolute() else base / audio_arg
    return Path(transcript.audio_file)


def to_wav(audio_path: Path, out_dir: Path, force: bool) -> Path:
    """pyannote is happiest with 16 kHz mono wav; convert non-wav inputs with ffmpeg.
    Also reused by docent_recognition.py, so it stays a standalone function."""
    if audio_path.suffix.lower() in _WAV_SUFFIXES:
        return audio_path

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        sys.exit("ffmpeg not found on PATH — needed to convert audio to wav for diarization.")

    out_dir.mkdir(parents=True, exist_ok=True)
    wav_path = out_dir / f"{audio_path.stem}_16k_mono.wav"
    if wav_path.exists() and not force:
        print(f"Reusing existing {wav_path.name} (use --force to reconvert).")
        return wav_path

    print(f"Converting {audio_path.name} -> {wav_path.name} (16 kHz mono)...")
    subprocess.run(
        [ffmpeg, "-y", "-i", str(audio_path), "-ac", "1", "-ar", "16000", str(wav_path)],
        check=True,
        capture_output=True,
    )
    return wav_path


def main():
    parser = argparse.ArgumentParser(description="Stap 2: couple diarization onto a transcript JSON")
    parser.add_argument("--transcript", required=True, help="Path to a Phase 1 transcript JSON")
    parser.add_argument("--audio", default=None, help="Override audio file (filename inside --dir, or a path)")
    parser.add_argument("--dir", choices=["raw", "test"], default="test")
    parser.add_argument("--min-speakers", type=int, default=None)
    parser.add_argument("--max-speakers", type=int, default=None)
    parser.add_argument("--min-cluster-size", type=int, default=None,
                        help="Override pyannote clustering.min_cluster_size (default: modelwaarde 12)")
    parser.add_argument("--clustering-threshold", type=float, default=None,
                        help="Override pyannote clustering.threshold (default: modelwaarde ~0.7046)")
    parser.add_argument("--no-refine", action="store_true",
                        help="Sprekergrens-verfijning (speaker_boundaries.py) overslaan — puur pyannote, oud gedrag")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--out", default=None, help="Output JSON path (default: Data-local/processed/diarization/)")
    parser.add_argument("--force", action="store_true", help="Redo wav conversion and overwrite output")
    args = parser.parse_args()

    transcript_path = Path(args.transcript)
    if not transcript_path.exists():
        sys.exit(f"Transcript JSON not found: {transcript_path}")
    transcript = WorkshopTranscript.model_validate_json(transcript_path.read_text(encoding="utf-8"))

    audio_path = _resolve_audio(transcript, args.audio, args.dir)
    if not audio_path.exists():
        sys.exit(f"Audio file not found: {audio_path}")

    DIARIZATION_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = Path(args.out) if args.out else DIARIZATION_OUTPUT_DIR / f"{transcript_path.stem}_diarized.json"
    if out_path.exists() and not args.force:
        sys.exit(f"{out_path} already exists. Use --force to overwrite.")

    wav_path = to_wav(audio_path, DIARIZATION_OUTPUT_DIR, args.force)

    config = DiarizationConfig(
        device=args.device,
        min_speakers=args.min_speakers,
        max_speakers=args.max_speakers,
        clustering_min_cluster_size=args.min_cluster_size,
        clustering_threshold=args.clustering_threshold,
        refine_boundaries=not args.no_refine,
    )

    print(f"Loading diarization backend '{config.backend}' ({config.hf_model}) on {config.device}...")
    backend = PyannoteBackend(config)

    print(f"Diarizing {wav_path.name}...")
    result = backend.diarize(
        wav_path, min_speakers=config.min_speakers, max_speakers=config.max_speakers
    )
    pyannote_summary = {
        "n_turns": len(result.turns),
        "raw_speakers": result.raw_speakers,
        "talk_seconds": {k: round(v, 2) for k, v in result.talk_time().items()},
    }

    refinement_meta = None
    if config.refine_boundaries:
        from config import BoundaryRefinementConfig
        print("Refining speaker boundaries (stem-embeddings per eenheid, zie speaker_boundaries.py)...")
        result, refinement_meta = refine_diarization(
            result, wav_path, transcript.segments, BoundaryRefinementConfig(device=config.device)
        )
        refinement_meta["pyannote_before_refinement"] = pyannote_summary

    label_info = build_label_map(result, main_speaker_min_share=config.main_speaker_min_share)
    new_segments = assign_speakers(
        transcript.segments,
        result.turns,
        label_info["map"],
        overlap_min_ratio=config.overlap_min_ratio,
        uncertain_coverage_below=config.uncertain_coverage_below,
        uncertain_margin_below=config.uncertain_margin_below,
        turn_confidence_below=config.turn_confidence_below if config.refine_boundaries else None,
    )
    stats = summarize(new_segments)

    diarization_meta = {
        "backend": result.backend,
        "model": result.model,
        "settings": result.settings,
        "runtime_seconds": result.runtime_seconds,
        "n_turns": len(result.turns),
        "raw_speakers": result.raw_speakers,
        "label_map": label_info["map"],
        "speaker_inventory": label_info["inventory"],
        "main_speaker_uncertain": label_info["main_speaker_uncertain"],
        "assignment_settings": {
            "overlap_min_ratio": config.overlap_min_ratio,
            "uncertain_coverage_below": config.uncertain_coverage_below,
            "uncertain_margin_below": config.uncertain_margin_below,
            "turn_confidence_below": config.turn_confidence_below if config.refine_boundaries else None,
        },
        "boundary_refinement": refinement_meta,   # None = niet verfijnd (--no-refine)
        "assignment": stats,
        "source_transcript": transcript_path.name,
        "audio_file": str(audio_path),
    }

    enriched = transcript.model_copy(update={"segments": new_segments, "diarization": diarization_meta})
    out_path.write_text(enriched.model_dump_json(indent=2), encoding="utf-8")

    print("\n--- diarization summary ---")
    print(f"raw speakers      : {result.raw_speakers}  ({len(result.turns)} turns)")
    for row in label_info["inventory"]:
        print(f"  {row['label']:<16} <- {row['raw']:<12} {row['talk_seconds']:>7.1f}s  ({row['share']*100:4.1f}%)")
    print(f"segments          : {stats['segments']}")
    print(f"  per label       : {json.dumps(stats['per_label'])}")
    print(f"  overlap         : {stats['overlap_segments']}")
    print(f"  uncertain       : {stats['uncertain_segments']}")
    print(f"  unassigned      : {stats['unassigned_segments']}")
    print(f"diarization time  : {result.runtime_seconds}s")
    if refinement_meta:
        rs = refinement_meta["stats"]
        merged = {k: v for k, v in refinement_meta["merge_map"].items() if k != v}
        print("--- boundary refinement ---")
        print(f"  pyannote vooraf : {pyannote_summary['raw_speakers']}  ({pyannote_summary['n_turns']} turns)")
        print(f"  samengevoegd    : {merged or 'geen'}")
        print(f"  nieuwe sprekers : {[n['label'] for n in refinement_meta['new_speakers']] or 'geen'}")
        print(f"  omgelabeld      : {rs['relabeled_seconds']}s   aangevuld: {rs['filled_seconds']}s   "
              f"geknipt: {rs['n_splits']}x   onduidelijk: {rs['unclear_seconds']}s")
        for c in refinement_meta["changes"]:
            if not c.get("split"):
                print(f"    {c['start']:7.2f}-{c['end']:7.2f}s  {c['from']} -> {c['to']}  ({c['reason']})")
        print(f"  runtime         : {refinement_meta['runtime_seconds']}s")
    print(f"\nwritten to {out_path}")


if __name__ == "__main__":
    main()
