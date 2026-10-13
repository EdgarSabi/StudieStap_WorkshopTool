"""Sjabloon voor JOUW eerste didactische indicator.

Dit bestand is een leeg skelet met uitleg, GEEN echte classifier. Zolang
`geimplementeerd = False` verzint het niets en antwoordt het NOT_IMPLEMENTED.

Stappen om er een echte indicator van te maken:
  1. Kies een naam voor je indicator (`name`) en beschrijf in woorden wat je zoekt.
  2. Schrijf je eigen logica in `zoek_fragment()`. Daar komt jouw NLP:
       - tokenization   : tekst in woorden splitsen
       - POS-tagging    : woordsoorten bepalen
       - regels         : bijv. patronen op woorden of zinsbouw
       - klassieke ML   : bijv. scikit-learn, zelf getraind op eigen gelabelde data
     (Installeer daarvoor zelf een pakket en zet het in pyproject.toml.)
  3. Zet `geimplementeerd = True`.
  4. Registreer de klasse in src/studiestap/classification/indicators.py (lijst INDICATORS).
  5. Schrijf een test met synthetische zinnen, zowel voorbeelden die WEL en NIET onder je
     indicator vallen (zie tests/test_classification.py als voorbeeld).

Eerlijkheidsregels van dit project:
  * Onzekere of ontbrekende gegevens -> NOT_ASSESSABLE of UNKNOWN, nooit raden.
  * DETECTED mag alleen met bewijsfragmenten (`Evidence`) erbij.
  * Een uitspraak van een leerling of onbekende rol telt alleen mee als jij daar bewust voor kiest.
"""
from __future__ import annotations

from typing import Optional

from studiestap.classification.base import (ConversationContext, Evidence, Indicator, IndicatorResult,
                                            IndicatorStatus, Utterance)


class MijnIndicator(Indicator):
    name = "mijn_eerste_indicator"
    geimplementeerd = False   # <- zet op True als je zoek_fragment() hebt geschreven

    def zoek_fragment(self, uiting: Utterance) -> Optional[str]:
        """Geef het letterlijke tekstfragment terug waaraan je de indicator herkent, of None.

        TODO (jouw werk): hier komt je tokenization / POS-tagging / regels / ML.
        """
        return None

    def classify(self, context: ConversationContext) -> IndicatorResult:
        if not self.geimplementeerd:
            return IndicatorResult(self.name, IndicatorStatus.NOT_IMPLEMENTED,
                                   explanation="Nog geen implementatie; er wordt niets geclassificeerd.")

        # Alleen uitingen waar we iets over mogen zeggen. (Pas dit aan op jouw onderzoeksvraag.)
        beoordeelbaar = [u for u in context.utterances if u.review_status != "NOT_ASSESSABLE"]
        if not beoordeelbaar:
            return IndicatorResult(self.name, IndicatorStatus.NOT_ASSESSABLE,
                                   explanation="Geen uitingen met bruikbare tekst.")

        bewijs = []
        for uiting in beoordeelbaar:
            fragment = self.zoek_fragment(uiting)
            if fragment:
                bewijs.append(Evidence(uiting.segment_id, fragment, note=f"rollen: {uiting.roles}"))

        if bewijs:
            return IndicatorResult(self.name, IndicatorStatus.DETECTED, bewijs,
                                   explanation=f"{len(bewijs)} fragment(en) gevonden.")
        # Niets gevonden is niet hetzelfde als 'het gebeurt niet': dat hangt af van de kwaliteit van de data.
        onzeker = [u for u in beoordeelbaar if u.review_status == "REVIEW_REQUIRED"]
        if onzeker:
            return IndicatorResult(self.name, IndicatorStatus.UNKNOWN,
                                   explanation=f"Niets gevonden, maar {len(onzeker)} uiting(en) hebben kwaliteitssignalen.")
        return IndicatorResult(self.name, IndicatorStatus.NOT_DETECTED, explanation="Niets gevonden.")
