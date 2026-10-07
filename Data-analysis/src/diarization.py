"""
STAP 2 — Speaker diarization: Wie spreekt wanneer. Hier worden nog geen labels aan de personen toegevoegd (zoals docent of andere spreker)
Dit gebeurt in een vervolgstap

Draaien:
    python diarization.py --transcript <Phase 1 JSON> [--audio ...] [--min-speakers N] [--max-speakers N] [--force]
    python diarization.py --transcript <Phase 1 JSON> --backend sortformer   # NVIDIA Sortformer i.p.v. pyannote

Twee backends met dezelfde interface: pyannote (default) en NVIDIA Streaming
Sortformer via NeMo (zie SortformerBackend hieronder). De backend levert
alleen SpeakerTurns; alles daarna is voor beide gelijk.

Uses pyannote.audio (or Sortformer) to find raw speaker
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
            },
            runtime_seconds=round(runtime, 2),
        )


# ============================================================
# NVIDIA Streaming Sortformer (via NeMo) — alternatieve backend
# ============================================================
# Waarom: pyannote doet eerst segmentatie en daarna clustering van
# stem-embeddings. Korte tussenkomsten ("Meneer.", "Hou op!") leveren te
# weinig embedding op en worden dan bij de dominante spreker geclusterd —
# precies het probleem uit de hyperparameter-tuning (Emma verdwijnt,
# spreker B in testaudio2 wordt bij A gezet). Sortformer heeft géén aparte
# clusteringstap: één end-to-end model voorspelt per frame van 80 ms voor
# elk van maximaal 4 sprekers of die actief is. Overlap is daardoor gewoon
# "twee sprekers tegelijk actief" in plaats van een bijproduct.
#
# Beperkingen (bewust hier opgeschreven):
#   - maximaal 4 sprekers. Bij een klas met meer sprekers worden stemmen in
#     die 4 "slots" samengevoegd. Voor ons doel (docent vs. de rest) is dat
#     minder erg dan het klinkt, maar het is GEEN volledige diarisatie van
#     een hele klas.
#   - getraind op vooral Engels; Nederlands is niet door NVIDIA getest.
#     Daarom eerst evalueren met
#     Experiments/diarization/sortformer/evaluate_sortformer.py.
#   - min_speakers / max_speakers worden door Sortformer genegeerd.
#
# Licentie: nvidia/diar_streaming_sortformer_4spk-v2.1 valt onder de NVIDIA
# Open Model License (commercieel gebruik toegestaan). Let op: de oudere
# nvidia/diar_sortformer_4spk-v1 is CC-BY-NC-4.0 (niet-commercieel).

# Streaming-instellingen uit de modelkaart, de variant met de hoogste
# latency en daarmee de beste nauwkeurigheid. Wij verwerken offline (hele
# opname achteraf), dus latency maakt ons niet uit.
SORTFORMER_STREAMING_DEFAULTS = {
    "chunk_len": 340,
    "chunk_right_context": 40,
    "fifo_len": 40,
    "spkcache_update_period": 300,
    "spkcache_len": 188,
}


def parse_sortformer_lines(lines: list[str]) -> list[SpeakerTurn]:
    """NeMo geeft per bestand regels als "0.500 3.120 speaker_0" terug.
    Zet ze om naar SpeakerTurns met pyannote-achtige ids (SPEAKER_00), zodat
    build_label_map() en assign_speakers() ongewijzigd blijven werken.
    Losse functie (zonder NeMo) zodat hij zonder model te testen is."""
    turns: list[SpeakerTurn] = []
    for line in lines:
        parts = str(line).split()
        if len(parts) < 3:
            continue
        start, end, raw = float(parts[0]), float(parts[1]), parts[2]
        idx = raw.rsplit("_", 1)[-1]
        speaker = f"SPEAKER_{int(idx):02d}" if idx.isdigit() else raw
        if end > start:
            turns.append(SpeakerTurn(start=start, end=end, speaker=speaker))
    turns.sort(key=lambda t: (t.start, t.end))
    return turns


class SortformerBackend:
    name = "sortformer"

    def __init__(self, config: DiarizationConfig):
        self.config = config

        try:
            import torch
            from nemo.collections.asr.models import SortformerEncLabelModel
        except ImportError as e:
            raise ImportError(
                "NeMo is not installed. Run:  pip install \"nemo_toolkit[asr]\"  "
                "(see Experiments/diarization/sortformer/README.md for Windows notes)"
            ) from e

        model_name = config.sortformer_model
        try:
            if Path(model_name).suffix == ".nemo" and Path(model_name).exists():
                self._model = SortformerEncLabelModel.restore_from(
                    restore_path=model_name, map_location=torch.device(config.device), strict=False
                )
            else:
                # Niet gated: geen HF-token nodig. Wordt de eerste keer gedownload
                # naar de HuggingFace-cache (~500 MB).
                self._model = SortformerEncLabelModel.from_pretrained(
                    model_name, map_location=torch.device(config.device)
                )
        except Exception as e:
            raise RuntimeError(f"Could not load Sortformer model '{model_name}'. Original error: {e}") from e

        self._model.eval()

        streaming = dict(SORTFORMER_STREAMING_DEFAULTS)
        streaming.update(config.sortformer_streaming or {})
        modules = self._model.sortformer_modules
        for key, value in streaming.items():
            if hasattr(modules, key):
                setattr(modules, key, value)
        self._streaming = streaming

    def _postprocessing_yaml(self, tmp_dir: Path) -> Optional[str]:
        """NeMo leest postprocessing-instellingen alleen uit een yaml-bestand.
        We schrijven de dict uit de config even naar een tijdelijk bestand."""
        params = self.config.sortformer_postprocessing
        if not params:
            return None
        if isinstance(params, (str, Path)):
            return str(params)
        lines = ["parameters:"] + [f"  {k}: {float(v)}" for k, v in params.items()]
        path = tmp_dir / "sortformer_postprocessing.yaml"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return str(path)

    def diarize(
        self,
        audio_path: Path,
        *,
        min_speakers: Optional[int] = None,
        max_speakers: Optional[int] = None,
    ) -> DiarizationResult:
        import tempfile

        if min_speakers is not None or max_speakers is not None:
            print("  (sortformer: min/max speakers worden genegeerd — model heeft vast 4 slots)")

        with tempfile.TemporaryDirectory() as tmp:
            pp_yaml = self._postprocessing_yaml(Path(tmp))
            start = time.time()
            output = self._model.diarize(
                audio=[str(audio_path)],
                batch_size=1,
                postprocessing_yaml=pp_yaml,
                verbose=False,
            )
            runtime = time.time() - start

        # diarize() geeft een lijst (één item per bestand) van regels terug,
        # of (regels, tensors) als include_tensor_outputs=True.
        if isinstance(output, tuple):
            output = output[0]
        turns = parse_sortformer_lines(output[0] if output else [])

        return DiarizationResult(
            turns=turns,
            backend=self.name,
            model=self.config.sortformer_model,
            settings={
                "device": self.config.device,
                "min_speakers": min_speakers,
                "max_speakers": max_speakers,
                "streaming": self._streaming,
                "postprocessing": self.config.sortformer_postprocessing,
            },
            runtime_seconds=round(runtime, 2),
        )


BACKENDS = {
    PyannoteBackend.name: PyannoteBackend,
    SortformerBackend.name: SortformerBackend,
}


def get_backend(config: DiarizationConfig):
    """Kies de backend op basis van config.backend ("pyannote" of "sortformer")."""
    try:
        cls = BACKENDS[config.backend]
    except KeyError:
        raise ValueError(f"Unknown diarization backend '{config.backend}'. Choose from: {sorted(BACKENDS)}")
    return cls(config)


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
) -> list[TranscriptSegment]:
    """Return a NEW list of segments with speaker fields filled in. Input untouched."""
    out: list[TranscriptSegment] = []

    for seg in segments:
        duration = max(0.0, seg.end - seg.start)

        per_speaker: dict[str, float] = {}
        for t in turns:
            ov = _overlap_seconds(seg.start, seg.end, t.start, t.end)
            if ov > 0:
                per_speaker[t.speaker] = per_speaker.get(t.speaker, 0.0) + ov

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

        out.append(seg.model_copy(update={
            "speaker": label_map.get(winner_raw, winner_raw),
            "speaker_raw": winner_raw,
            "speaker_confidence": round(confidence, 4),
            "overlap": (runner_ov / duration) >= overlap_min_ratio,
            "uncertain_assignment": (
                coverage < uncertain_coverage_below or margin < uncertain_margin_below
            ),
        }))

    return out


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
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--backend", choices=sorted(BACKENDS), default=None,
                        help="Diarisatiemodel: pyannote of sortformer (default: DiarizationConfig.backend)")
    parser.add_argument("--sortformer-model", default=None,
                        help="Ander Sortformer-model (HF-naam of pad naar .nemo); default uit config.py")
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
    )
    if args.backend:
        config.backend = args.backend
    if args.sortformer_model:
        config.sortformer_model = args.sortformer_model

    model_name = config.sortformer_model if config.backend == "sortformer" else config.hf_model
    print(f"Loading diarization backend '{config.backend}' ({model_name}) on {config.device}...")
    backend = get_backend(config)

    print(f"Diarizing {wav_path.name}...")
    result = backend.diarize(
        wav_path, min_speakers=config.min_speakers, max_speakers=config.max_speakers
    )

    label_info = build_label_map(result, main_speaker_min_share=config.main_speaker_min_share)
    new_segments = assign_speakers(
        transcript.segments,
        result.turns,
        label_info["map"],
        overlap_min_ratio=config.overlap_min_ratio,
        uncertain_coverage_below=config.uncertain_coverage_below,
        uncertain_margin_below=config.uncertain_margin_below,
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
        },
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
    print(f"\nwritten to {out_path}")


if __name__ == "__main__":
    main()
