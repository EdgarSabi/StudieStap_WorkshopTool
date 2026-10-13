"""Command-line-interface.

    studiestap analyze    "C:\\Audio\\voorbeeld.mp3" [--teacher-reference docent.mp3]
    studiestap transcribe "C:\\Audio\\voorbeeld.mp3"
    studiestap check                       # wat is er lokaal beschikbaar?
    studiestap clean output\\voorbeeld_ab12cd34   # lokale rungegevens verwijderen
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import sys
from pathlib import Path

from . import __version__
from .models import StepRecord, StepStatus, StudieStapError
from .output.exporter import delete_run
from .pipeline import Reporter, run_pipeline
from .settings import get_hf_token, load_environment, load_settings

SYMBOL = {StepStatus.SUCCEEDED: "OK", StepStatus.PARTIAL: "GEDEELTELIJK", StepStatus.UNAVAILABLE: "NIET BESCHIKBAAR",
          StepStatus.FAILED: "MISLUKT", StepStatus.SKIPPED: "OVERGESLAGEN"}


class ConsoleReporter(Reporter):
    def on_start(self, name: str, description: str) -> None:
        print(f"  ... {description}", flush=True)

    def on_done(self, record: StepRecord) -> None:
        cache = " (hergebruikt uit eerdere run)" if record.reused_from_cache else ""
        print(f"  [{SYMBOL[record.status]}] {record.name}{cache}: {record.message}", flush=True)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="studiestap", description="StudieStap 2.0 - audiopipeline voor workshopreflectie")
    p.add_argument("--version", action="version", version=f"studiestap {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    def common(sp):
        sp.add_argument("audio", help="Pad naar een MP3- of WAV-bestand (tussen aanhalingstekens bij spaties)")
        sp.add_argument("--config", help="Pad naar config.yaml (standaard: ./config.yaml)")
        sp.add_argument("--out", help="Uitvoermap (standaard: output.directory uit config.yaml)")
        sp.add_argument("--force", action="store_true", help="Alles opnieuw berekenen, ook als er al resultaten zijn")
        sp.add_argument("--debug", action="store_true", help="Toon technische details bij fouten")

    a = sub.add_parser("analyze", help="Volledige analyse: tekst, sprekers, uitlijning, kwaliteit")
    common(a)
    a.add_argument("--teacher-reference", help="Referentieopname van de docent (nodig voor docentherkenning)")
    a.add_argument("--no-align", action="store_true", help="Sla woorduitlijning over")

    t = sub.add_parser("transcribe", help="Alleen transcriberen")
    common(t)

    sub.add_parser("check", help="Toon wat er lokaal beschikbaar is (pakketten, ffmpeg, modelcache)")

    c = sub.add_parser("clean", help="Verwijder een runmap met lokale gegevens")
    c.add_argument("run_dir", help="Pad naar de runmap (bevat run_manifest.json)")
    c.add_argument("--yes", action="store_true", help="Niet om bevestiging vragen")
    return p


def _cmd_run(args) -> int:
    settings = load_settings(Path(args.config) if args.config else None)
    if args.out:
        settings.output.directory = args.out
    mode = args.command
    print(f"StudieStap {mode}: {args.audio}")
    report = run_pipeline(
        args.audio, settings, mode=mode, force=args.force, debug=args.debug,
        teacher_reference=getattr(args, "teacher_reference", None),
        skip_alignment=getattr(args, "no_align", False),
        reporter=ConsoleReporter(),
    )
    problems = [r for r in report.steps if r.status in (StepStatus.FAILED, StepStatus.UNAVAILABLE)]
    print()
    if not report.ok:
        print("De analyse is gestopt: zonder transcriptie valt er niets te analyseren.")
        for r in report.steps:
            if r.status == StepStatus.FAILED:
                print(f"  Mislukte stap: {r.name} - {r.message}")
        print(f"Details: {report.run_dir}")
        return 1
    if problems:
        print("Klaar, maar let op - deze stappen leverden niet alles:")
        for r in problems:
            print(f"  - {r.name} ({SYMBOL[r.status].lower()}): {r.message}")
    else:
        print("Klaar.")
    print(f"Uitvoer staat in: {report.run_dir.resolve()}")
    if report.result_path:
        print(f"Hoofdbestand:     {report.result_path.resolve()}")
    return 0


def _hf_cache_dir() -> Path:
    if os.environ.get("HF_HUB_CACHE"):
        return Path(os.environ["HF_HUB_CACHE"])
    return Path(os.environ.get("HF_HOME", Path.home() / ".cache" / "huggingface")) / "hub"


def _cmd_check(_args) -> int:
    print(f"Python        : {sys.version.split()[0]}")
    print(f"ffmpeg        : {'gevonden' if shutil.which('ffmpeg') else 'NIET gevonden'}")
    for label, module in [("faster-whisper", "faster_whisper"), ("pyannote.audio", "pyannote.audio"),
                          ("whisperx", "whisperx"), ("torch", "torch")]:
        try:
            found = importlib.util.find_spec(module) is not None
        except ModuleNotFoundError:
            found = False
        print(f"{label:<14}: {'geinstalleerd' if found else 'niet geinstalleerd'}")
    print(f"HF_TOKEN      : {'ingesteld' if get_hf_token() else 'niet ingesteld'}  (waarde wordt nooit getoond)")
    cache = _hf_cache_dir()
    print(f"Modelcache    : {cache}")
    for model in ["Systran/faster-whisper-medium", "pyannote/speaker-diarization-3.1", "pyannote/segmentation-3.0",
                  "pyannote/wespeaker-voxceleb-resnet34-LM", "jonatasgrosman/wav2vec2-large-xlsr-53-dutch"]:
        present = (cache / ("models--" + model.replace("/", "--"))).exists()
        print(f"  {model:<48} {'in cache' if present else 'niet in cache'}")
    return 0


def _cmd_clean(args) -> int:
    run_dir = Path(args.run_dir)
    if not args.yes:
        answer = input(f"Alle bestanden in '{run_dir}' definitief verwijderen? Typ 'ja' om door te gaan: ")
        if answer.strip().lower() != "ja":
            print("Afgebroken; er is niets verwijderd.")
            return 1
    delete_run(run_dir)
    print(f"Verwijderd: {run_dir}")
    return 0


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except AttributeError:
            pass
    args = _build_parser().parse_args(argv)
    try:
        load_environment()
        if args.command in ("analyze", "transcribe"):
            return _cmd_run(args)
        if args.command == "check":
            return _cmd_check(args)
        return _cmd_clean(args)
    except StudieStapError as e:
        print(f"\nFout: {e.message}", file=sys.stderr)
        if e.hint:
            print(f"Tip:  {e.hint}", file=sys.stderr)
        if getattr(args, "debug", False):
            raise
        return 1
    except KeyboardInterrupt:
        print("\nAfgebroken door gebruiker.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
