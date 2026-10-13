# Verliesloze uitbreiding sprekerkoppeling — rapport

Branch `feature/lossless-speaker-intersections` (afgesplitst van `main` @ `0a4ab99d811c945a39ff11d4c6a74a83a1540609`). **Niets gecommit**: de wijzigingen staan in de werkboom van de branch, zodat jij ze kunt beoordelen. Grondslag: `baseline_cause_review.md` (ChatGPT Work, "gedeeltelijk bevestigd") en de eigen baseline-analyse.
Geen modelrun, geen nieuwe modellen, geen wijziging van drempels, instellingen, ground truths, modelgewichten of baselineresultaten.

## 1. Wat is gewijzigd (3 bronbestanden, +46/−1 regels; patch: [changes.patch](changes.patch))

| Bestand | Wijziging |
|---|---|
| [models.py](../../../src/models.py) | Nieuw model `RawSpeakerIntersection` (`speaker_raw`, `start`, `end`, `duration`). `TranscriptSegment` krijgt `raw_speaker_intersections` (lijst, standaard leeg) en `multiple_raw_speakers` (bool, standaard `False`). `SpeakerTurn` krijgt `raw_speaker_seconds` (dict, standaard leeg) en `multiple_raw_speakers`. Alleen toevoegingen met standaardwaarden: oude JSON laadt ongewijzigd. |
| [diarization.py](../../../src/diarization.py) | In `assign_speakers`: voor elke ruwe beurt met positieve overlap wordt de intersection (`max(begin)`, `min(eind)`, duur) vastgelegd, gesorteerd op (begin, eind, label) en op het segment gezet; `multiple_raw_speakers` = ≥ 2 verschillende ruwe labels. De winnaarsberekening (`per_speaker`, `ranked`, `coverage`, `margin`, `confidence`, `overlap`, `uncertain_assignment`) is **niet aangeraakt**. |
| [preprocessing.py](../../../src/preprocessing.py) | In `build_speaker_turns.close()`: `raw_speaker_seconds` (per ruw label som van intersectieduur over de bronsegmenten) en `multiple_raw_speakers` (any over bronsegmenten). Groepering/samenvoeging van turns is **ongewijzigd**. De volledige intersections blijven per segment beschikbaar in `turn.source_segments` (die embedden de volledige segmenten). |

Bestandsregeleinden (CRLF) zijn behouden; geen enkel ander bestand in `src/` is gewijzigd. Nieuwe tests: [test_speaker_intersections.py](../../../src/tests/test_speaker_intersections.py) (16 tests).

**Betekenis (ook in de docstrings):** een intersection is alleen tijdrekenkunde tussen één ASR-segment en één ruwe diarizatiebeurt. Het is **geen woordniveau-toewijzing** (de tekst wordt niet gesplitst of gedupliceerd) en geen bewijs dat `SPEAKER_01` een fysiek persoon is. `multiple_raw_speakers` betekent alleen "≥ 2 ruwe labels hebben positieve overlap met dit segment"; niet "tegelijk", niet "significant". Er is bewust geen drempel toegevoegd.

## 2. Hashes

| Bestand | Vóór | Na |
|---|---|---|
| `config.py` | `de727ea6…` | ongewijzigd |
| `diarization.py` | `cfa384c5…` | `fb805466…` (gewijzigd) |
| `models.py` | `dcbb063b…` | `102232b4…` (gewijzigd) |
| `preprocessing.py` | `4ba85fc3…` | `6248979d…` (gewijzigd) |
| `transcription.py`, `docent_recognition.py`, `run_docent_pipeline.py` | `153b7fa3…`, `af63ff65…`, `74ae0f6a…` | ongewijzigd |

Volledige lijsten: [source_hashes_before.txt](source_hashes_before.txt), [source_hashes_after.txt](source_hashes_after.txt). Gevolg voor het evaluatieprotocol: de `src`-hashes in `PROTOCOL.md` §1 gelden voor `main` @ `0a4ab99`; een run op deze branch vraagt een protocolnotitie (v2) met de nieuwe hashes.

## 3. Verwachte uitkomsten (vooraf vastgelegd in de testkop) en resultaat

| # | Verwachting (uit tijdsrekenkunde) | Resultaat |
|---|---|---|
| T1 | Segment 2,5–7 s, beurten A 0–4, B 4–6, A 6–10 → intersections A 2,5–4,0, B 4,0–6,0, A 6,0–7,0; dominant A (2,5 s > 2,0 s) en overige legacy-waarden (confidence 0,5556, overlap, onzeker) ongewijzigd; `multiple` = True; na preprocessing `raw_speaker_seconds = {A: 2,5, B: 2,0}`; tekst intact; overleeft JSON-rondreis | geslaagd |
| T2 | A 0–10 + B 4–6, segment 4–6 → A 4–6 en B 4–6 (elk 2,0 s), identiek voor beide beurtvolgordes. De dominante keuze bij exacte gelijkstand blijft het bestaande volgordeafhankelijke gedrag (A-eerst → A, B-eerst → B) en is zo vastgelegd, niet veranderd | geslaagd |
| T3 | Bewaarde runs 1 en 2, zonder modelrun: alle legacy-velden van alle 19 segmenten gelijk aan de bewaarde uitvoer; dominant nog steeds alleen `SPEAKER_00`; `SPEAKER_01` in precies de segmenten 1, 4, 5, 11, 12, 15, 16, samen 3,898125 s; seconden per ruw label gelijk aan een onafhankelijke 1-ms-rasterberekening; preprocessing geeft dezelfde 10 turns | geslaagd |
| C | Controle: A 0–4, B 4–6, A 6–10 met ASR-grenzen 0–4, 4–6, 6–10 → A, B, A zonder meersprekerstatus | geslaagd |
| T4 | Normaal segment (A 0–10, segment 1–3): 1 intersection, `multiple` = False; beurten die het segment alleen op de rand raken: niet meegeteld; geen overlappende beurt: lege lijst, `speaker=None`, `multiple` = False; twee beurten van hetzelfde label: beide intervallen, `multiple` = False | geslaagd |
| Compat | Oude JSON zonder de nieuwe velden laadt met lege standaardwaarden | geslaagd |

**Falsificatie:** bewust foute representaties (alleen dominante intersection bewaren; tweede intersection weglaten; turnsamenvatting zonder minderheidsspreker; strippen van `SPEAKER_01`) worden door dezelfde controles afgekeurd (4 tests). Daarnaast: de nieuwe tests draaien tegen de **oude** code (`git show HEAD`) met alleen een lege klasse-shim zodat de import slaagt: **14 van 16 mislukken**; de twee die slagen zijn precies de twee die bestaand gedrag vastleggen (dominant label en tiegedrag), zoals bedoeld ([tests_new_on_OLD_code.txt](tests_new_on_OLD_code.txt)).

## 4. Bestaande tests en regressies

| Suite | Vóór | Na |
|---|---|---|
| `Data-analysis/src/tests` | 17 OK | 33 OK (17 + 16 nieuw) |
| `Experiments/classification/tests` | 51 OK | 51 OK |
| `Experiments/baseline_evaluation/tests` (evaluatieharnas) | 52 OK | 52 OK |

**Regressies: geen.** Uitvoer: `tests_before_*.txt`, `tests_after_*.txt` in deze map. Opmerking: `tests_before_src.txt` bevat ook een printregel van een bestaande test die een pad naar `Data-local/processed/docent_recognition/…` toont; die test mockt de subprocessen en schrijft niets (zie volgende punt).
Integriteit: alle opgeslagen uitvoerhashes van baselinerun 1 en 2 (`run_result.json`) zijn nog gelijk aan de bestanden op schijf; de vier gewijzigde/nieuwe bestanden zijn de enige verschillen in de werkboom (naast de al eerder ongetrackte bestanden).

## 5. Voor/na op de bewaarde ruwe beurten ([before_after_stored_runs.json](before_after_stored_runs.json), [script](before_after_stored_runs.py), [uitvoer](before_after_stored_runs_output.txt))

| | Vóór | Na |
|---|---|---|
| Dominant label (19 segmenten, run 1 én 2) | `SPEAKER_00` ×19 | `SPEAKER_00` ×19; alle legacy-velden identiek |
| Ruwe sprekers zichtbaar in de segmenten | `SPEAKER_00` | `SPEAKER_00` en **`SPEAKER_01`** |
| Segmenten met meerdere ruwe sprekers | niet uitgedrukt (alleen `overlap` voor 5 segmenten) | 7: segmenten 1, 4, 5, 11, 12, 15, 16 |
| Seconden `SPEAKER_01` in de segmenten | 0 (niet bewaard) | 3,898125 s van de 3,898125 s ruw; `SPEAKER_00` 29,142156 s |
| Turns (preprocessing) | 10 | 10, zelfde grenzen, flags en sprekers |
| `SPEAKER_01` per turn | niet zichtbaar | turns 1 (0,726 s), 3 (0,650 s), 4 (1,072 s), 6 (0,571 s), 7 (0,292 s), 8 (0,588 s) |

Voorbeeld segment 7,0–9,0 s: `[SPEAKER_00 7,0–9,0 (2,0 s); SPEAKER_01 8,35–9,0 (0,65 s)]`, dominant `SPEAKER_00` (ongewijzigd). Run 1 en run 2 geven identieke intersections.

## 6. Wat de wijziging wel oplost

- Het verlies van reeds door pyannote gevonden sprekeractiviteit in de segmentrepresentatie en in de turns: `SPEAKER_01` is nu na koppeling en preprocessing herleidbaar, met exacte tijdsintervallen en duur, ook bij opeenvolgende sprekers in één segment (T1) en bij gelijktijdigheid (T2), onafhankelijk van beurtvolgorde.
- Latere evaluatie kan aan de hand van de intersections bepalen of een segment meerdere ruwe labels bevat, zonder terug te gaan naar het RTTM.
- Achterwaartse compatibiliteit: bestaande velden, dominante keuze, thresholds en turngroepering zijn aantoonbaar gelijk op de bewaarde runs; oude JSON blijft laden.

## 7. Wat de wijziging niet oplost

- **De pyannote-fout zelf.** Van referentie-B (4,0 s) valt maar 0,62 s in `SPEAKER_01`; 1,5 s zonder overlapvlag zit volledig in `SPEAKER_00`. Dat staat nu hetzelfde in de intersections: het blijft een upstream-afwijking.
- **Eén label per tekstsegment.** Het dominante label en de tekst zijn onveranderd; geen splitsing van segmenten, geen woordtoewijzing. Elke consument die één spreker per tekstfragment nodig heeft, krijgt niet automatisch een betere.
- **Geen consument gebruikt de nieuwe velden.** Docentherkenning embedt nog steeds de hele turn; classificatie en evaluatieharnas (`segment_eval`) lezen ze niet. De informatie is beschikbaar, niet toegepast.
- **`multiple_raw_speakers` is aanwezigheid, geen betekenis.** Segment 12 krijgt de vlag door een sliver van 0,020 s `SPEAKER_01` (18,00–18,02 s). Zonder drempel (conform opdracht) moeten consumenten de duur gebruiken. Het zegt niets over gelijktijdigheid of over de juistheid van het label.
- **Merge-regel ongewijzigd.** Een segment met een geringe tweede spreker (onder de bestaande overlapgrens van 15 %) wordt nog steeds in een turn gemerged (turn 7 bevat zo 0,292 s `SPEAKER_01`); dat is nu wel zichtbaar via `raw_speaker_seconds` en `multiple_raw_speakers`.
- **Gelijkstand bij dominant label** blijft volgordeafhankelijk (bestaand gedrag, vastgelegd in een test).
- **Niet-exclusieve ruwe beurten** (pyannote 4.x `exclusive_speaker_diarization`) zijn niet onderzocht; intersections van een label overlappen daarom soms met die van een ander label in dezelfde tijd, wat de bedoeling is (herleidbaarheid), niet een fysieke overlapclaim.
- Ruwe labels zijn clusterlabels; of `SPEAKER_01` de leerling is, blijft onbewezen.

## 8. Reproduceren

```bash
Data-analysis/src/.venv/Scripts/python.exe -B -m unittest discover -s Data-analysis/src/tests -t Data-analysis/src
```

(vanuit `Data-analysis/src` draaien, zoals de bestaande tests). Voor/na: `before_after_stored_runs.py --out <nieuw bestand>.json`.
