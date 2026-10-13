"""Register van indicatoren. Voorlopig LEEG: er zijn geen didactische indicatoren ingebouwd.

Een eigen indicator toevoegen:
  1. Schrijf een klasse die `Indicator` erft (zie examples/mijn_indicator.py).
  2. Zet een instantie van die klasse in INDICATORS hieronder.
  3. Draai `studiestap analyze ...`: het resultaat verschijnt onder "classification".

Waar komt jouw NLP-code? In de methode `classify` van je klasse. Je kunt daar
gebruikmaken van:
  - tokenization (tekst in woorden splitsen),
  - POS-tagging (woordsoorten bepalen),
  - eigen regels (bijv. patronen op woorden),
  - klassieke ML (bijv. scikit-learn) die je zelf traint op je eigen gelabelde data.
Voeg daarvoor zelf de nodige pakketten toe aan pyproject.toml.
"""
from __future__ import annotations

from .base import ConversationContext, Indicator, IndicatorResult

INDICATORS: list[Indicator] = []   # <- hier komen jouw indicatoren


def run_indicators(context: ConversationContext, indicators: list[Indicator] | None = None) -> dict:
    """Draai alle geregistreerde indicatoren en geef een JSON-klaar resultaat."""
    indicators = INDICATORS if indicators is None else indicators
    results: list[IndicatorResult] = []
    for indicator in indicators:
        try:
            results.append(indicator.classify(context))
        except Exception as e:  # een kapotte indicator mag de rest van de analyse niet slopen
            from .base import IndicatorStatus
            results.append(IndicatorResult(indicator.name, IndicatorStatus.UNKNOWN,
                                           explanation=f"Indicator crashte: {type(e).__name__}: {e}"))
    return {
        "status": "NOT_IMPLEMENTED" if not indicators else "RAN",
        "note": "Geen didactische indicatoren ingebouwd; voeg ze toe in classification/indicators.py."
                if not indicators else "Resultaten zijn indicaties voor reflectie, geen beoordeling.",
        "indicators": results,
    }
