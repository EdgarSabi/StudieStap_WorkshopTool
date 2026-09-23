# Fase 5A — classification foundation

Technische basis voor de classificatiefase. **Bouwt geen didactische
classificatie** — de mockclassifier retourneert uitsluitend vaste
testresultaten, de prompt is een placeholder, en er is geen scoringssysteem.
Doel: bewijzen dat de technische pipeline (transcript laden → contextvenster
kiezen → prompt bouwen → classifier aanroepen → resultaat valideren →
reproduceerbaar opslaan) werkt, met beide bestaande transcriptbronnen.

Raakt `Data-analysis/src` niet aan — importeert alleen read-only
(`models.processed.ProcessedTranscript`), zoals de eerdere experimenten.

## Structuur

```
classification/
├── _common.py                 paden (RAW_DIR, OUTPUT_DIR), zet Data-analysis/src op sys.path
├── schemas/
│   ├── turn.py                 ClassificationTurn + FragmentTurns (licht, ontkoppeld van models.processed.SpeakerTurn)
│   └── result.py                STAP 5: ClassificationResult (met status OK/UNKNOWN)
├── loaders/
│   ├── manual.py                 STAP 2: laadt jouw {fragment_id, speaker_mapping, turns:[...]}-formaat
│   ├── pipeline.py               STAP 2: laadt een bestaande ProcessedTranscript-JSON (Fase 3-output)
│   └── __init__.py               load_fragment(): detecteert automatisch welk formaat het is
├── context/
│   └── selector.py               STAP 3: contextvensters A/B/C, index-based
├── classifiers/
│   ├── base.py                    STAP 4: Classifier-interface + RawModelOutput
│   ├── prompt.py                  losstaande promptbouwer (placeholder-template, geversioneerd)
│   └── mock.py                    MockClassifier: uitsluitend vaste, canned resultaten
├── run_classification.py          STAP 6: orkestreert alles, schrijft 1 reproduceerbare JSON per run
└── tests/
    ├── fixtures/                  kleine, fictieve, COMMITTABLE testfixtures (2 formaten)
    ├── test_loaders.py
    ├── test_context_selector.py
    ├── test_schema.py
    └── test_run_classification.py
```

## Twee inputformaten, één pipeline

`loaders.load_fragment(path)` detecteert automatisch welk formaat een JSON-
bestand is en geeft in beide gevallen hetzelfde `FragmentTurns`-object terug
— de rest van de pipeline (contextselectie, classificatie) weet niet en hoeft
niet te weten welke bron het was:

- **Handmatig** (`speaker_mapping` in het JSON): jouw
  `Data-local/raw/classification/test_classification_01.json`-formaat.
  Geen timestamps, geen onzekerheidsinformatie — `start`/`end` blijven
  `None`, en `uncertain_assignment`/`overlap` worden **expliciet `None`**
  ("onbekend"), nooit stilzwijgend `False` ("bekend betrouwbaar"). Contextvensters
  werken puur op turn-volgorde, dus ontbrekende timestamps zijn geen probleem.
- **Bestaande pipeline-output** (`source_transcript_path` in het JSON): een
  Fase 3 `ProcessedTranscript`-JSON (bv. via `run_preprocessing.py`
  gegenereerd). Timestamps én de echte, automatisch bepaalde
  `uncertain_assignment`/`overlap`-waarden worden **ongewijzigd overgenomen**
  (`True`/`False`, nooit gereset naar `None`).

Dat onderscheid (`None` = onbekend vs. `False` = bekend schoon) is met opzet
nooit samengevoegd — zie `schemas/turn.py`'s docstring en
`context/selector.py`'s `unknown_reliability`/`flagged_uncertain`-vlaggen
per contextvenster.

## Draaien

Geen nieuwe dependencies — bestaande venv:

```bash
Data-analysis/src/.venv/Scripts/python.exe Data-analysis/Experiments/classification/run_classification.py --input Data-local/raw/classification/test_classification_01.json --mode B
```

`--mode` kiest A/B/C (zie hieronder), `--indicator` accepteert een
(herhaalbare) indicator-id (default: één placeholder-indicator, want er zijn
nog geen echte indicatoren gedefinieerd), `--force` overschrijft bestaande
output. Werkt identiek op een `ProcessedTranscript`-JSON:

```bash
Data-analysis/src/.venv/Scripts/python.exe Data-analysis/Experiments/classification/run_classification.py --input Data-local/processed/preprocessing/<fragment>_turns.json --mode C
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

Geverifieerd (zie `tests/test_context_selector.py` en de drie
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

**36/36 tests slagen.** Gedekt (zie STAP 7-eisen): transcript correct
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
- **Prompt is een placeholder** (`classifiers/prompt.py`, versie
  `placeholder-v0`) — bevat geen didactische indicatordefinitie, alleen de
  contextturns en een indicator-id.
- **`unknown_reliability`/`flagged_uncertain` zijn per-venster, niet
  per-turn** — een venster met één schone en één onzekere turn wordt als
  geheel `flagged_uncertain=True`; welke specifieke turn dat veroorzaakte is
  wel terug te vinden (elke turn in `raw_outputs`/de prompt draagt zijn eigen
  `uncertain_assignment`/`overlap`), maar wordt niet apart samengevat.
- **`context_uncertain_before/after` (tijdgat-gebaseerd, uit
  `preprocessing/context.py`) wordt niet hergebruikt** — bewust, want dat
  vereist timestamps die een handmatig transcript niet heeft. De
  contextselector hier werkt uitsluitend op turn-volgorde.
- **Geen validatie tegen een derde/vierde inputformaat** (bv. een ruwe Fase
  1/2 `WorkshopTranscript`-JSON zonder turns) — daarvoor zou eerst
  `run_preprocessing.py` gedraaid moeten worden (bestaande tool, hergebruikt
  je eigen turn-merge-logica), dit experiment doet dat niet automatisch.
- **`status` is bewust geen Pydantic `Literal`/enum** (zie `schemas/result.py`)
  — een simpele stringcheck, zodat een status als `"ERROR"` later zonder
  schemawijziging toegevoegd kan worden. Pipeline-fouten (bv. een
  classifier die een exception gooit) landen nu in `run_classification.py`'s
  eigen `errors`-lijst, niet in `ClassificationResult.status`.

## Wat is nodig om een echt taalmodel aan te sluiten

1. **Een nieuwe `Classifier`-implementatie** in `classifiers/` (bv.
   `claude.py` of `local_llm.py`) die `classifiers.base.Classifier`
   implementeert: `classify(prompt, *, indicator_id) -> RawModelOutput`. De
   rest van de pipeline (`run_classification.py`, contextselectie, schema)
   hoeft niet te veranderen — dat is precies waarom de interface zo klein is.
2. **Echte indicatordefinities** — die zijn er nog niet (expliciet buiten
   scope van Fase 5A). `classifiers/prompt.py::build_prompt()` moet dan de
   werkelijke definitie/instructie per `indicator_id` gaan meenemen in plaats
   van de huidige placeholder-tekst, en `PROMPT_VERSION` ophogen.
3. **Resultaatparsing/-validatie robuuster maken**: een echt taalmodel geeft
   vrije tekst/JSON terug die niet altijd netjes parseert — de nieuwe
   `Classifier`-implementatie moet dat omzetten naar `RawModelOutput` (of
   zelf `status="UNKNOWN"` teruggeven bij een onparseerbaar antwoord), zodat
   `schemas/result.py`'s validatie niet crasht op een onverwacht modelantwoord.
4. **API-credentials/rate limiting/kosten** — geen onderdeel van dit
   experiment; hoort thuis in de nieuwe classifier-implementatie zelf
   (bv. via een `.env`-variabele, zoals `HF_TOKEN` nu al voor pyannote werkt).
5. **Een echte foutstatus overwegen** (`status="ERROR"` naast `"UNKNOWN"`)
   zodra "het model faalde" en "het model wist het niet" van elkaar
   onderscheiden moeten worden — nu bewust nog niet toegevoegd (zie
   Beperkingen).
6. **Grotere/echte testtranscripten** — dit experiment is getest op één
   fictief 20-turns-fragment en kleine synthetische unit-testfixtures; een
   representatieve set (langer, meerdere sprekers, met echte
   pipeline-onzekerheid) is nodig vóór een productie-uitspraak over
   betrouwbaarheid.
