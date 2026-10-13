"""Alle gegevensvormen van de pipeline op een plek.

We gebruiken gewone `dataclass`-klassen: een klasse met alleen velden. Met
`to_dict()` (onderaan) wordt alles JSON. Dit bestand bevat geen logica, alleen
"hoe ziet een gegeven eruit".

Belangrijke spelregel: *ruwe* gegevens (wat het model teruggaf) en *afgeleide*
gegevens (wat wij ervan maken) staan in aparte klassen en aparte JSON-bestanden.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from enum import Enum
from typing import Any, Optional


class StudieStapError(Exception):
    """Een fout die we aan de gebruiker in gewoon Nederlands kunnen uitleggen.

    `hint` zegt wat je eraan kunt doen. De CLI toont beide, zonder traceback.
    """

    def __init__(self, message: str, hint: str = ""):
        super().__init__(message)
        self.message = message
        self.hint = hint


class StepStatus(str, Enum):
    SUCCEEDED = "succeeded"      # geslaagd
    PARTIAL = "partial"          # gedeeltelijk geslaagd
    UNAVAILABLE = "unavailable"  # niet beschikbaar (pakket/model/referentie ontbreekt)
    FAILED = "failed"            # mislukt
    SKIPPED = "skipped"          # bewust overgeslagen (bijv. --no-align)


class ReviewStatus(str, Enum):
    """Ruimte voor de latere kwaliteitsregels (onderzoeksfases 3 en 4).

    Let op: dit is GEEN bewezen betrouwbaarheid. Zie quality/checks.py.
    """
    ASSESSABLE = "ASSESSABLE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    NOT_ASSESSABLE = "NOT_ASSESSABLE"


# ---------------------------------------------------------------- audio

@dataclass
class AudioInfo:
    source_path: str              # originele bestand; wordt nooit gewijzigd of verplaatst
    sha256: str                   # vingerafdruk van de inhoud (herkent dezelfde opname)
    size_bytes: int
    duration_seconds: float
    source_format: str            # bijv. "mp3"
    working_wav: Optional[str] = None   # tijdelijke 16 kHz mono-kopie voor de modellen


# ---------------------------------------------------------------- transcriptie (ruw)

@dataclass
class Segment:
    id: int
    start: float
    end: float
    text: str
    avg_logprob: Optional[float] = None       # ruwe Whisper-signalen, ongewijzigd bewaard
    no_speech_prob: Optional[float] = None
    compression_ratio: Optional[float] = None


@dataclass
class Transcript:
    language: str
    duration_seconds: float
    model: str
    settings: dict
    runtime_seconds: float
    segments: list[Segment] = field(default_factory=list)


# ---------------------------------------------------------------- diarizatie (ruw)

@dataclass
class SpeakerInterval:
    """Een ruw interval van het diarizatiemodel. Intervallen van verschillende
    sprekers mogen elkaar overlappen: dat is echte gelijktijdige activiteit."""
    speaker: str      # modellabel, bijv. "SPEAKER_00" (geen persoon, geen rol)
    start: float
    end: float


@dataclass
class Diarization:
    backend: str
    model: str
    settings: dict
    runtime_seconds: float
    intervals: list[SpeakerInterval] = field(default_factory=list)


# ---------------------------------------------------------------- woorduitlijning

@dataclass
class Word:
    text: str
    start: Optional[float] = None   # None = de aligner kon dit woord geen tijd geven
    end: Optional[float] = None
    score: Optional[float] = None


@dataclass
class AlignedSegment:
    segment_id: int
    words: list[Word] = field(default_factory=list)
    status: StepStatus = StepStatus.SUCCEEDED   # per segment: succeeded / partial / failed


@dataclass
class WordAlignment:
    status: StepStatus
    message: str
    model: Optional[str] = None
    language: Optional[str] = None
    runtime_seconds: float = 0.0
    segments: list[AlignedSegment] = field(default_factory=list)


# ---------------------------------------------------------------- sprekerkoppeling (afgeleid)

@dataclass
class Intersection:
    """Overlap van precies een ruw sprekerinterval met een segment/woord."""
    speaker: str
    start: float
    end: float
    duration: float


@dataclass
class WordSpeaker:
    """Sprekerkoppeling van een woord. `speaker` is alleen gevuld bij status
    SINGLE; bij AMBIGUOUS staan alle kandidaten in `candidates` en kiezen we niet."""
    index: int
    text: str
    start: Optional[float]
    end: Optional[float]
    status: str                        # SINGLE | AMBIGUOUS | NO_SPEAKER | NO_TIMING
    speaker: Optional[str] = None
    candidates: list[str] = field(default_factory=list)


@dataclass
class SegmentSpeakers:
    segment_id: int
    intersections: list[Intersection]      # ALLE overlappen, ongefilterd
    seconds_per_speaker: dict[str, float]  # samenvatting: unie van intervallen per spreker
    simultaneous_seconds: float            # tijd waarin >= 2 sprekers tegelijk actief zijn
    uncovered_seconds: float               # tijd zonder enige spreker
    attribution: str                       # SINGLE | PARTIAL | MIXED | NONE
    dominant_speaker: Optional[str] = None  # ALLEEN een samenvatting, niet de volle waarheid
    dominant_share: Optional[float] = None  # aandeel van de segmentduur
    words: list[WordSpeaker] = field(default_factory=list)


# ---------------------------------------------------------------- docentrollen

@dataclass
class SpeakerRole:
    """Identiteit en rol zijn gescheiden. Een spreker-ID is geen rol.

    identity_status: MATCH | NO_MATCH | UNKNOWN | NO_REFERENCE
    role: "docent" alleen bij MATCH; anders "onbekend" (we noemen niemand
          automatisch "leerling").
    """
    speaker: str
    identity_status: str
    role: str
    similarity: Optional[float] = None    # ruwe cosinusgelijkenis, GEEN kans
    n_clips: int = 0
    note: str = ""


# ---------------------------------------------------------------- stemconsistentie (optionele diagnostiek)

@dataclass
class SegmentVoiceCheck:
    """Past de stem in dit segment bij het toegekende ruwe sprekerlabel? Alleen een waarneming.

    verdict: CONSISTENT | CLOSER_TO_OTHER_SPEAKER | INCONCLUSIVE (met `reason`).
    Scores zijn ruwe cosinuswaarden, geen kansen.
    """
    segment_id: int
    speaker: Optional[str]                 # het toegekende (dominante) ruwe label
    verdict: str
    reason: str = ""
    own_similarity: Optional[float] = None    # clip vs. profiel van het toegekende label
    other_speaker: Optional[str] = None       # het andere label dat het best past
    other_similarity: Optional[float] = None
    own_lowest_typical: Optional[float] = None  # laagste score van eigen clips (zie voice_consistency.py)
    clip: Optional[tuple[float, float]] = None  # welk stuk audio is vergeleken


# ---------------------------------------------------------------- kwaliteit

@dataclass
class Signal:
    code: str
    detail: str
    segment_id: Optional[int] = None   # None = geldt voor de hele opname
    kind: str = "observed"             # "observed" = waargenomen; nooit "proven_unreliable"


@dataclass
class SegmentQuality:
    segment_id: int
    status: ReviewStatus
    signals: list[Signal] = field(default_factory=list)


@dataclass
class QualityReport:
    note: str
    global_signals: list[Signal] = field(default_factory=list)
    segments: list[SegmentQuality] = field(default_factory=list)


# ---------------------------------------------------------------- stapregistratie

@dataclass
class StepRecord:
    name: str
    status: StepStatus
    message: str = ""
    output_file: Optional[str] = None
    runtime_seconds: float = 0.0
    reused_from_cache: bool = False


def to_dict(obj: Any) -> Any:
    """Dataclass (ook geneste) -> gewone dict/list, klaar voor JSON."""
    if is_dataclass(obj) and not isinstance(obj, type):
        return {k: to_dict(v) for k, v in asdict(obj).items()}
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, dict):
        return {k: to_dict(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_dict(v) for v in obj]
    return obj
