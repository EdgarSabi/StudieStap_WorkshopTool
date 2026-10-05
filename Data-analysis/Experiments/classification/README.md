# Fase 5A — classification foundation

Technische basis voor de classificatiefase. **Bouwt geen didactische
classificatie** — de mockclassifier retourneert uitsluitend vaste
testresultaten, de prompt is een placeholder, en er is geen scoringssysteem.
Doel: bewijzen dat de technische pipeline (transcript laden → contextvenster
kiezen → prompt bouwen → classifier aanroepen → resultaat valideren →
reproduceerbaar opslaan) werkt, met beide bestaande transcriptbronnen.

Raakt `Data-analysis/src` niet aan — importeert alleen read-only
(`models.ProcessedTranscript`), zoals de eerdere experimenten.

## Structuur

**Update (opschoning):** wat eerst 6 submappen met 14 losse bestanden was
(`schemas/`, `loaders/`, `context/`, `classifiers/`, `_common.py`,
`run_classification.py`) is nu 2 bestanden, precies zoals bij de andere
pipeline-stappen in `Data-analysis/src`:

```
classification/
├── classification_data.py     data + laden: ClassificationTurn/FragmentTurns,
│                               load_manual_fixture()/load_pipeline_processed()/load_fragment()
│                               (STAP 2), contextvensters A/B/C (STAP 3), ClassificationResult (STAP 5)
├── classification.py          gedrag + CLI: promptbouwer (STAP 4), MockClassifier (STAP 4),
│                               run() + argparse (STAP 6) — importeert uit classification_data.py
└── tests/
    ├── fixtures/               kleine, fictieve, COMMITTABLE testfixtures (2 formaten)
    ├── test_classification_data.py   laden, contextvensters, schema-validatie
    └── test_classification.py         promptekst + volledige route (mockclassifier, alle modes)
```

Twee bestanden in plaats van één, omdat "data + laden + contextvensters"
(`classification_data.py`, ~300 regels) en "prompt + classificeren + CLI"
(`classification.py`, ~185 regels) twee losse, goed te onderscheiden
verantwoordelijkheden zijn — samen in één bestand persen zou het juist
onoverzichtelijker maken dan nu.

## Twee inputformaten, één pipeline

`classification_data.load_fragment(path)` detecteert automatisch welk
formaat een JSON-bestand is en geeft in beide gevallen hetzelfde
`FragmentTurns`-object terug — de rest van de pipeline (contextselectie,
classificatie) weet niet en hoeft niet te weten welke bron het was:

- **Handmatig** (`speaker_mapping` in het JSON): jouw
  `Data-local/raw/classification/test_classification_01.json`-formaat.
  Geen timestamps, geen onzekerheidsinformatie — `start`/`end` blijven
  `None`, en `uncertain_assignment`/`overlap` worden **expliciet `None`**
  ("onbekend"), nooit stilzwijgend `False` ("bekend betrouwbaar"). Contextvensters
  werken puur op turn-volgorde, dus ontbrekende timestamps zijn geen probleem.
- **Bestaande pipeline-output** (`source_transcript_path` in het JSON): een
  Fase 3 `ProcessedTranscript`-JSON (bv. via `preprocessing.py`
  gegenereerd). Timestamps én de echte, automatisch bepaalde
  `uncertain_assignment`/`overlap`-waarden worden **ongewijzigd overgenomen**
  (`True`/`False`, nooit gereset naar `None`).

Dat onderscheid (`None` = onbekend vs. `False` = bekend schoon) is met opzet
nooit samengevoegd — zie `classification_data.py`'s docstring en zijn
`unknown_reliability`/`flagged_uncertain`-vlaggen per contextvenster.

## Draaien

Geen nieuwe dependencies — bestaande venv:

```bash
Data-analysis/src/.venv/Scripts/python.exe Data-analysis/Experiments/classification/classification.py --input Data-local/raw/classification/test_classification_01.json --mode B
```

`--mode` kiest A/B/C (zie hieronder), `--indicator` accepteert een
(herhaalbare) indicator-id (default: één placeholder-indicator, want er zijn
nog geen echte indicatoren gedefinieerd), `--force` overschrijft bestaande
output. Werkt identiek op een `ProcessedTranscript`-JSON — inclusief eentje
die door `docent_recognition.py` verrijkt is met `docent_role`:

```bash
Data-analysis/src/.venv/Scripts/python.exe Data-analysis/Experiments/classification/classification.py --input Data-local/processed/docent_recognition/<fragment>_docent_roles.json --mode C
```

Output: `Data-local/processed/classification/<fragment_id>__<mode>__mock.json`
— bevat input, contextconfiguratie, promptversie, modelconfiguratie, de ruwe
modeloutput én de gevalideerde resultaten per spreekbeurt, plus een
`errors`-lijst (STAP 6, volledig reproduceerbaar).

## Contextvensters A/B/C — geverifieerd op `test_classification_01.json`

20 turns, dus 20 resultaten per mode (1 per turn, nooit dubbel — zie
`context.selector.iter_context_windows()`: elke turn is precies één keer
`center_turn_id`).

| Mode | Regel | Turn 1 (rand) | Turn 10 (midden) | Turn 20 (rand) |
|---|---|---|---|---|
| A | alleen huidige | `[1]` | `[10]` | `[20]` |
| B | vorige + huidige | `[1]` (geen vorige) | `[9, 10]` | `[19, 20]` |
| C | 2×vorige + huidige + volgende | `[1, 2]` (geen vorige) | `[8, 9, 10, 11]` | `[18, 19, 20]` (geen volgende) |

Geverifieerd (zie `tests/test_classification_data.py` en de drie
`Data-local/processed/classification/test_classification_01__{A,B,C}__mock.json`-
runs): aan de randen van het fragment wordt correct geclipt (geen crash,
geen niet-bestaande turn-id), en `center_turn_id` zit in elk venster altijd
in `context_turn_ids`. Alle 20 turns in dit fixture hebben
`uncertain_assignment`/`overlap` = `None` (handmatig transcript, geen
signaal) → elk venster krijgt `unknown_reliability=True`, `flagged_uncertain=False`.

## Testen

```bash
Data-analysis/src/.venv/Scripts/python.exe -m unittest discover -s Data-analysis/Experiments/classification/tests -t Data-analysis/Experiments/classification
```

**51/51 tests slagen** (2 bestanden: `test_classification_data.py` +
`test_classification.py`). Gedekt (zie STAP 7-eisen): transcript correct
ingeladen (beide formaten), contextvensters selecteren de juiste turns
(incl. randgevallen), centrale turn blijft herkenbaar, JSON-validatie werkt
(incl. afgewezen ongeldige status), UNKNOWN wordt afgehandeld (niet
weggelaten, `detected=None`), oorspronkelijke inputbestanden blijven
byte-voor-byte ongewijzigd, en onzekere speakerlabels blijven behouden —
zowel de échte `True`/`False`-waarden uit een automatische transcriptie als
het expliciete `None` ("onbekend") bij een handmatig transcript.

## Beperkingen

- **Geen echte classificatie.** MockClassifier retourneert een vaste,
  cyclische reeks (`True`/`OK`, `False`/`OK`, `None`/`UNKNOWN`) die niets met
  de inhoud van een turn te maken heeft — puur om de pipeline te testen.
- **Prompt is een placeholder** (`classification.py::build_prompt()`, versie
  `placeholder-v1`) — bevat geen didactische indicatordefinitie, alleen de
  contextturns (incl. `docent_role`) en een indicator-id.
- **`unknown_reliability`/`flagged_uncertain`/`docent_role_unresolved` zijn
  per-venster, niet per-turn** — een venster met één schone en één onzekere
  turn wordt als geheel `flagged_uncertain=True`; welke specifieke turn dat
  veroorzaakte is wel terug te vinden (elke turn in `raw_outputs`/de prompt
  draagt zijn eigen `uncertain_assignment`/`overlap`/`docent_role`), maar
  wordt niet apart samengevat.
- **`context_uncertain_before/after` (tijdgat-gebaseerd, uit
  `preprocessing.py`) wordt niet hergebruikt** — bewust, want dat vereist
  timestamps die een handmatig transcript niet heeft. De contextselector
  hier werkt uitsluitend op turn-volgorde.
- **Geen validatie tegen een derde/vierde inputformaat** (bv. een ruwe Fase
  1/2 `WorkshopTranscript`-JSON zonder turns) — daarvoor zou eerst
  `preprocessing.py` gedraaid moeten worden (bestaande tool, hergebruikt je
  eigen turn-merge-logica), dit experiment doet dat niet automatisch.
- **`status` is bewust geen Pydantic `Literal`/enum** (zie
  `classification_data.py::ClassificationResult`) — een simpele stringcheck,
  zodat een status als `"ERROR"` later zonder schemawijziging toegevoegd kan
  worden. Pipeline-fouten (bv. een classifier die een exception gooit)
  landen nu in `classification.py::run()`'s eigen `errors`-lijst, niet in
  `ClassificationResult.status`.

## Wat is nodig om een echt taalmodel aan te sluiten

1. **Een nieuwe classifier** in `classification.py` (of een eigen bestand
   ernaast, bv. `claude_classifier.py`): een object/klasse met `name`,
   `version` en een `classify(prompt, indicator_id) -> dict`-methode die
   `{"detected", "evidence", "status", "raw"}` teruggeeft — precies wat
   `MockClassifier` nu ook doet. De rest van de pipeline (`run()`,
   contextselectie, schema) hoeft niet te veranderen; alleen `main()`'s regel
   `classifier = MockClassifier()` wordt dan `classifier = ClaudeClassifier()`.
2. **Echte indicatordefinities** — die zijn er nog niet (expliciet buiten
   scope van Fase 5A). `classification.py::build_prompt()` moet dan de
   werkelijke definitie/instructie per `indicator_id` gaan meenemen in plaats
   van de huidige placeholder-tekst, en `PROMPT_VERSION` ophogen.
3. **Resultaatparsing/-validatie robuuster maken**: een echt taalmodel geeft
   vrije tekst/JSON terug die niet altijd netjes parseert — de nieuwe
   classifier moet dat omzetten naar `{"detected", "evidence", "status", "raw"}`
   (of zelf `status="UNKNOWN"` teruggeven bij een onparseerbaar antwoord),
   zodat `ClassificationResult`'s validatie niet crasht op een onverwacht
   modelantwoord.
4. **API-credentials/rate limiting/kosten** — geen onderdeel van dit
   experiment; hoort thuis in de nieuwe classifier zelf (bv. via een
   `.env`-variabele, zoals `HF_TOKEN` nu al voor pyannote werkt).
5. **Een echte foutstatus overwegen** (`status="ERROR"` naast `"UNKNOWN"`)
   zodra "het model faalde" en "het model wist het niet" van elkaar
   onderscheiden moeten worden — nu bewust nog niet toegevoegd (zie
   Beperkingen).
6. **Grotere/echte testtranscripten** — dit experiment is getest op één
   fictief 20-turns-fragment en kleine synthetische unit-testfixtures; een
   representatieve set (langer, meerdere sprekers, met echte
   pipeline-onzekerheid) is nodig vóór een productie-uitspraak over
   betrouwbaarheid.
