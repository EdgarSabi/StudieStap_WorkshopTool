"""Lege classificatie-interface: hier komt later JOUW didactische NLP-code.

Er is bewust GEEN echte classifier, geen verzonnen regels, geen LLM en geen
modeltraining. Een indicator die nog niet geschreven is, antwoordt eerlijk
NOT_IMPLEMENTED in plaats van iets te verzinnen.

Hoe werkt het?
  1. Pipeline maakt een `ConversationContext`: de uitspraken (tekst, spreker,
     rol-/kwaliteitsinformatie) in volgorde.
  2. Elke indicator is een klasse met `name` en `classify(context)`.
  3. `classify` geeft een `IndicatorResult` terug met een status, optioneel
     bewijsfragmenten (`Evidence`) en een uitleg.

Zie docs/HOW_IT_WORKS.md en examples/mijn_indicator.py voor een stap-voor-stapvoorbeeld.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class IndicatorStatus(str, Enum):
    DETECTED = "DETECTED"                # de indicator is aangetroffen (met bewijs!)
    NOT_DETECTED = "NOT_DETECTED"        # onderzocht en niet aangetroffen
    UNKNOWN = "UNKNOWN"                  # kan geen uitspraak doen (te onzeker)
    NOT_ASSESSABLE = "NOT_ASSESSABLE"    # gegevens ontbreken/ontoereikend
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"  # er is nog geen implementatie


@dataclass
class Utterance:
    """Een uitspraak, zoals een classifier hem ziet. Niet-ingevuld = onbekend, niet 'nee'."""
    segment_id: int
    start: float
    end: float
    text: str
    speakers: list[str] = field(default_factory=list)     # ruwe sprekerlabels in dit segment
    roles: list[str] = field(default_factory=list)        # bijv. ["docent"] of ["onbekend"]
    review_status: str = "REVIEW_REQUIRED"                 # ASSESSABLE / REVIEW_REQUIRED / NOT_ASSESSABLE
    signals: list[str] = field(default_factory=list)       # codes van kwaliteitssignalen


@dataclass
class ConversationContext:
    utterances: list[Utterance]
    language: str = "nl"


@dataclass
class Evidence:
    segment_id: int
    quote: str            # letterlijk fragment uit de tekst
    note: str = ""


@dataclass
class IndicatorResult:
    indicator: str
    status: IndicatorStatus
    evidence: list[Evidence] = field(default_factory=list)
    explanation: str = ""


class Indicator:
    """Basis voor een didactische indicator. Erf hiervan en overschrijf `classify`."""

    name: str = "naamloze_indicator"

    def classify(self, context: ConversationContext) -> IndicatorResult:
        # Standaard: nog niet geschreven. Verzin niets.
        return IndicatorResult(self.name, IndicatorStatus.NOT_IMPLEMENTED,
                               explanation="Nog geen implementatie voor deze indicator.")
