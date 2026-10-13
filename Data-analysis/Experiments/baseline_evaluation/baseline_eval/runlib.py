"""Veilige uitvoer, invoerchecks en het in-process draaien van de ORIGINELE main()-functies met omgeleide uitvoerpaden.

Niets hier wijzigt bestanden in Data-analysis/src: alleen module-variabelen in het draaiende proces worden tijdelijk
omgezet (en daarna hersteld), zodat de originele code zijn uitvoer naar de nieuwe evaluatiemap schrijft."""
import contextlib
import hashlib
import io
import json
import os
import platform
import subprocess
import sys
import time
import traceback
from pathlib import Path


class OutputExistsError(Exception):
    pass


class AudioUnreadableError(Exception):
    pass


def new_dir(path) -> Path:
    """Maakt een NIEUWE map; bestaat die al (ook leeg) dan stoppen we. Nooit hergebruiken."""
    p = Path(path)
    try:
        p.mkdir(parents=True, exist_ok=False)
    except FileExistsError as e:
        raise OutputExistsError(f"Uitvoermap bestaat al, wordt niet overschreven: {p}") from e
    return p


def write_new(path, text: str) -> Path:
    p = Path(path)
    try:
        with open(p, "x", encoding="utf-8") as f:
            f.write(text)
    except FileExistsError as e:
        raise OutputExistsError(f"Uitvoerbestand bestaat al, wordt niet overschreven: {p}") from e
    return p


def write_json_new(path, obj) -> Path:
    return write_new(path, json.dumps(obj, indent=2, ensure_ascii=False, default=str))


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def probe_audio(path) -> float:
    """Duur in seconden via ffprobe; duidelijke fout bij ontbrekend of onleesbaar bestand."""
    p = Path(path)
    if not p.is_file():
        raise AudioUnreadableError(f"Audiobestand ontbreekt: {p}")
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                           capture_output=True, text=True, timeout=60)
    except FileNotFoundError as e:
        raise AudioUnreadableError("ffprobe niet gevonden op PATH (hoort bij ffmpeg)") from e
    out = r.stdout.strip()
    try:
        dur = float(out)
    except ValueError:
        raise AudioUnreadableError(f"Audiobestand niet leesbaar als audio: {p} ({r.stderr.strip()[:200] or 'geen duur'})")
    if dur <= 0:
        raise AudioUnreadableError(f"Audiobestand heeft duur 0: {p}")
    return dur


def tree_snapshot(root, patterns=("**/*",)) -> dict:
    """pad -> (grootte, mtime_ns). Voor het 'niets aangeraakt'-bewijs voor bestaande caches en code."""
    root = Path(root)
    snap = {}
    if not root.exists():
        return snap
    for pat in patterns:
        for f in root.glob(pat):
            if f.is_file() and "__pycache__" not in f.parts:
                st = f.stat()
                snap[str(f)] = (st.st_size, st.st_mtime_ns)
    return snap


def diff_snapshots(a: dict, b: dict) -> dict:
    return {"added": sorted(set(b) - set(a)), "removed": sorted(set(a) - set(b)),
            "changed": sorted(k for k in set(a) & set(b) if a[k] != b[k])}


def run_original_main(module, argv: list, patches: dict, log_path=None) -> dict:
    """Roept module.main() aan met sys.argv en tijdelijk omgezette module-variabelen. Vangt SystemExit en fouten af
    en bewaart ze (nooit stil). Geeft status/duur/stdout terug."""
    saved_argv, saved = sys.argv, {k: getattr(module, k) for k in patches}
    buf = io.StringIO()
    status, detail = "ok", None
    t0 = time.time()
    try:
        sys.argv = [f"{module.__name__}.py"] + [str(a) for a in argv]
        for k, v in patches.items():
            setattr(module, k, v)
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            module.main()
    except SystemExit as e:
        if e.code not in (0, None):
            status, detail = "exit", str(e.code)
    except BaseException as e:  # noqa: BLE001 - alles bewaren
        status, detail = "error", "".join(traceback.format_exception(type(e), e, e.__traceback__))
    finally:
        sys.argv = saved_argv
        for k, v in saved.items():
            setattr(module, k, v)
    res = {"stage": module.__name__, "status": status, "detail": detail, "seconds": round(time.time() - t0, 2),
           "stdout": buf.getvalue()}
    if log_path:
        write_new(log_path, buf.getvalue() + (f"\n--- {status}: {detail}\n" if detail else ""))
    return res


def _pkg_versions(names) -> dict:
    from importlib import metadata
    out = {}
    for n in names:
        try:
            out[n] = metadata.version(n)
        except metadata.PackageNotFoundError:
            out[n] = None
    return out


def hf_snapshots(models) -> dict:
    """Revisie-hashes uit de lokale HF-cache (geen netwerk)."""
    base = Path(os.environ.get("HF_HOME", Path.home() / ".cache" / "huggingface")) / "hub"
    out = {}
    for m in models:
        d = base / ("models--" + m.replace("/", "--")) / "snapshots"
        out[m] = sorted(p.name for p in d.iterdir()) if d.is_dir() else None
    return out


def git_state(repo) -> dict:
    def g(*a):
        r = subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True)
        return r.stdout.strip()
    return {"head": g("rev-parse", "HEAD"), "branch": g("branch", "--show-current"),
            "status_short": g("status", "--short").splitlines()}


def environment(src_dir, token_present: bool) -> dict:
    return {
        "python": sys.version, "platform": platform.platform(), "cpu_count": os.cpu_count(),
        "packages": _pkg_versions(["faster-whisper", "ctranslate2", "torch", "torchaudio", "pyannote.audio", "pyannote.core",
                                   "pyannote.metrics", "speechbrain", "numpy", "scipy", "pydantic", "python-dotenv",
                                   "huggingface-hub"]),
        "hf_snapshots": hf_snapshots(["Systran/faster-whisper-medium", "pyannote/speaker-diarization-3.1",
                                      "pyannote/segmentation-3.0", "pyannote/wespeaker-voxceleb-resnet34-LM"]),
        "hf_token_present": bool(token_present),   # alleen aanwezig ja/nee; waarde wordt nooit gelezen of gelogd
        "hf_hub_offline": os.environ.get("HF_HUB_OFFLINE"),
        "src_sha256": {p.name: sha256(p) for p in sorted(Path(src_dir).glob("*.py"))},
    }
