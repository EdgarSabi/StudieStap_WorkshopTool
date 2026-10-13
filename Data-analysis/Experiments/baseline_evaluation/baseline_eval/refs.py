"""Referenties lezen (alleen lezen; nooit schrijven naar de bronbestanden) en afgeleide gegevens bouwen."""
import csv
import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from pyannote.core import Annotation, Segment, Timeline


class ReferenceProblem(Exception):
    """Referentie ontbreekt of is niet bruikbaar. Altijd met pad en reden."""


@dataclass
class RefRow:
    line: int
    start: float
    end: float
    speaker_id: str
    kind: str                 # speech | nonspeech | unknown | unlabelled | cut
    role: Optional[str]
    overlap: Optional[bool]
    intelligible: Optional[str]
    unintelligible: Optional[str]   # afgeleid, zelfde waarden: ja = moeilijk/niet verstaanbaar. Alleen kwaliteitswaarschuwing.
    note: str
    text: str


@dataclass
class Reference:
    fragment: str
    path: Path
    sha256: str
    columns: list
    rows: list = field(default_factory=list)

    @property
    def has_speaker_labels(self) -> bool:
        return any(r.kind == "speech" for r in self.rows)

    def speakers(self) -> list:
        return sorted({r.speaker_id for r in self.rows if r.kind == "speech"})


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _tri(v: str) -> Optional[bool]:
    v = (v or "").strip().lower()
    return True if v == "ja" else False if v == "nee" else None


def _kind(spk: str, note: str) -> str:
    if "niet meenemen" in (note or "").lower():
        return "cut"                      # eigen instructie van de annotator in de notitie
    s = spk.strip().upper()
    if s == "GEEN":
        return "nonspeech"
    if s == "ONBEKEND":
        return "unknown"
    if not s:
        return "unlabelled"
    return "speech"


def load_reference(path, fragment: str = "") -> Reference:
    path = Path(path)
    if not path.is_file():
        raise ReferenceProblem(f"Referentiebestand ontbreekt: {path}")
    try:
        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            cols = list(reader.fieldnames or [])
            raw = list(reader)
    except (OSError, UnicodeDecodeError, csv.Error) as e:
        raise ReferenceProblem(f"Referentie niet leesbaar: {path}: {e}") from e
    need = {"start_seconds", "end_seconds", "speaker_id"}
    if not need <= set(cols):
        raise ReferenceProblem(f"{path.name}: verplichte kolommen ontbreken: {sorted(need - set(cols))}")
    tcol = next((c for c in ("transcript", "transcript_hint") if c in cols), None)
    ref = Reference(fragment or path.stem, path, sha256_file(path), cols)
    for i, r in enumerate(raw, start=2):
        try:
            s, e = float(r["start_seconds"]), float(r["end_seconds"])
        except (TypeError, ValueError) as ex:
            raise ReferenceProblem(f"{path.name} regel {i}: ongeldige tijd ({ex})") from ex
        if not (e > s >= 0):
            raise ReferenceProblem(f"{path.name} regel {i}: eindtijd {e} moet groter zijn dan begintijd {s} (>= 0)")
        intel = ((r.get("intelligible") or "").strip().lower() or None) if "intelligible" in cols else None
        note = (r.get("note") or "").strip()
        spk = (r["speaker_id"] or "").strip()
        ref.rows.append(RefRow(
            line=i, start=s, end=e, speaker_id=spk, kind=_kind(spk, note),
            role=((r.get("speaker_role") or "").strip().lower() or None) if "speaker_role" in cols else None,
            overlap=_tri(r.get("overlap", "")), intelligible=intel, unintelligible=intel, note=note,
            text=(r.get(tcol) or "").strip() if tcol else ""))
    if not ref.rows:
        raise ReferenceProblem(f"{path.name}: geen rijen")
    return ref


def speaker_roles(ref: Reference, override: Optional[dict] = None) -> dict:
    """speaker_id -> docent|leerling. Tegenspraak -> ReferenceProblem."""
    m: dict = {}
    for r in ref.rows:
        if r.kind == "speech" and r.role in ("docent", "leerling"):
            if m.setdefault(r.speaker_id, r.role) != r.role:
                raise ReferenceProblem(f"{ref.path.name}: {r.speaker_id} heeft meerdere rollen")
    for k, v in (override or {}).items():
        if m.get(k, v) != v:
            raise ReferenceProblem(f"rolbron en referentie spreken elkaar tegen voor {k}")
        m[k] = v
    return m


def speech_annotation(ref: Reference, duration: Optional[float] = None) -> Annotation:
    """Alleen bekende sprekers. ONBEKEND/GEEN/cut worden NOOIT een spreker. Gelijktijdige sprekers blijven behouden."""
    a = Annotation(uri=ref.fragment)
    for r in ref.rows:
        if r.kind != "speech":
            continue
        e = min(r.end, duration) if duration else r.end
        if e > r.start:
            a[Segment(r.start, e)] = r.speaker_id
    return a


def masked_timeline(ref: Reference, duration: float, overlap_mode: str = "keep",
                    kinds=("nonspeech", "unknown", "cut")) -> Timeline:
    segs = []
    for r in ref.rows:
        s, e = r.start, min(r.end, duration)
        if e <= s:
            continue
        if r.kind in kinds or (overlap_mode == "exclude" and r.kind == "speech" and r.overlap):
            segs.append(Segment(s, e))
    tl = Timeline(segs)
    if overlap_mode == "exclude":
        tl = Timeline(list(tl) + list(speech_annotation(ref, duration).get_overlap()))
    return tl.support()


def build_uem(ref: Reference, duration: float, uem_mode: str, overlap_mode: str) -> Timeline:
    if uem_mode == "strict":
        base = Timeline([Segment(0, duration)])
    elif uem_mode == "labelled":
        base = speech_annotation(ref, duration).get_timeline().support()
    else:
        raise ValueError(f"onbekende uem_mode {uem_mode}")
    return masked_timeline(ref, duration, overlap_mode).gaps(support=base)


def reference_text(ref: Reference) -> str:
    rows = sorted((r for r in ref.rows if r.kind not in ("nonspeech", "cut")), key=lambda r: (r.start, r.end))
    return " ".join(r.text for r in rows if r.text)


def has_overlapping_text_rows(ref: Reference, tol: float = 0.05) -> bool:
    rows = sorted((r for r in ref.rows if r.kind not in ("nonspeech", "cut") and r.text), key=lambda r: r.start)
    return any(b.start < a.end - tol for a, b in zip(rows, rows[1:]))


_LABEL = re.compile(r"^\s*(docent|leerling(?:\s*\d+)?)\s*:\s*", re.I)


def manual_txt_text(path) -> str:
    path = Path(path)
    if not path.is_file():
        raise ReferenceProblem(f"Handmatige transcriptie ontbreekt: {path}")
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = _LABEL.sub("", line).strip().strip('"“”')
        if line:
            out.append(line)
    return " ".join(out)
