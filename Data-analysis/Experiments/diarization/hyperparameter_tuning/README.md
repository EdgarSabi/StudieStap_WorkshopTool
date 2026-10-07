# Handmatige ground truth voor diarisatie-hyperparameter-tuning

Dit is **geen productiecode** en raakt de bestaande pipeline (`Data-analysis/src/`) niet aan.
Het is puur bedoeld om straks `clustering.min_cluster_size` (en eventueel
`clustering.threshold`) te kunnen testen tegen iets betrouwbaars, in plaats
van alleen op het oog te beoordelen.

## Waarom dit anders is dan de bestaande `manual_labels`

De `manual_labels` in `Notebooks/04-diarization.ipynb` zijn **rol-labels**
(DOCENT/OTHER/IGNORE) op losse, vooraf uitgeknipte chunks voor het
stemherkenning-experiment. Voor diarisatie-tuning hebben we iets anders
nodig: wie spreekt wanneer, over de **hele, doorlopende tijdlijn** van een
fragment, met een eigen ID per spreker (niet per rol) — inclusief de
plekken waar mensen echt door elkaar praten.

## Hoe in te vullen (`ground_truth_template.csv`)

Eén rij per spreekbeurt, in volgorde. Luister het fragment gewoon af en
noteer:

| Kolom | Betekenis |
|---|---|
| `fragment` | bestandsnaam zonder extensie, bv. `testaudio4_fragment` |
| `turn_index` | volgnummer binnen het fragment, begint bij 0 |
| `start_seconds` / `end_seconds` | begin/eind van de spreekbeurt in seconden (bv. `72.5`) |
| `speaker_id` | een eigen label per persoon die je hoort, bv. `SPREKER_A`, `SPREKER_B`, `SPREKER_C`. Gebruik **dezelfde letter voor dezelfde persoon** binnen één fragment. Het maakt niet uit wie de docent is — dat hoeft hier niet apart genoteerd te worden. |
| `overlap` | `ja` als je twee mensen tegelijk hoort praten in dit stukje, anders `nee` |
| `note` | optioneel — alles wat je opvalt (bv. "geroezemoes op achtergrond", "onduidelijk wie") |

Precisie tot op de seconde is genoeg, je hoeft niet te knippen op milliseconde.
Bij twijfel: liever een grove, eerlijke inschatting dan een gegokt precies getal.

De eerste 4 rijen (met `VOORBEELD_` in de fragmentnaam) zijn een voorbeeld
om het formaat te laten zien — verwijder die voordat je je eigen rijen
toevoegt.

## Welke fragmenten aan te raden

Voorstel, maar kies gerust anders als jij een beter idee hebt welk fragment
waar illustratief voor is:

- **`testaudio4_fragment`** — hier verdween een 3e spreker volledig
  (zie het diarisatie-experiment); goed fragment om `min_cluster_size` op
  te testen.
- **`testaudio2_fragment`** — hierin merged de pipeline twee verschillende
  sprekers in één turn zonder dat overlap/onzeker werd gevlagd (zie de
  toelichting onderaan `Data-analysis/src/docent_recognition.py`); goed
  fragment voor "verkeerde samenvoeging".
- **Eén extra fragment als check achteraf** (bv. `testaudio6_fragment`,
  omdat we die diarisatie al goed kennen uit eerdere tests) — dit fragment
  NIET gebruiken om de parameter op te kiezen, alleen om achteraf te
  controleren of de gekozen instelling ook daar nog klopt. Zo voorkomen we
  dat we toevallig alleen op de eerste twee fragmenten optimaliseren.

Twee fragmenten van elk 1-2 minuten is genoeg om mee te beginnen — dit hoeft
geen uitputtende annotatie te worden, alleen genoeg om de vergelijking
straks eerlijk te maken.

---

# Resultaten en conclusie

## Wat er gedaan is

- Ground truth handmatig gelabeld (sprekers + tijden, startpunt voorgevuld uit
  de Whisper-segmenten, daarna handmatig gecontroleerd en aangepast):
  - `ground_truth_testaudio4_fragment.csv` — 120 s, 4 sprekers
  - `ground_truth_testaudio2_fragment.csv` — 30 s, 2 sprekers
- `evaluate_min_cluster_size.py` draait de bestaande pyannote-pipeline
  (`pyannote/speaker-diarization-3.1`, via `diarization.PyannoteBackend`) met
  een andere clustering-instelling en vergelijkt de uitkomst met de ground
  truth. De productiecode in `Data-analysis/src/` is niet gewijzigd.
- Commando om te draaien (vanuit `Data-analysis/src`):

  ```
  .venv\Scripts\python.exe ..\Experiments\diarization\hyperparameter_tuning\evaluate_min_cluster_size.py testaudio4_fragment --param min_cluster_size --values 12 8
  .venv\Scripts\python.exe ..\Experiments\diarization\hyperparameter_tuning\evaluate_min_cluster_size.py testaudio2_fragment --param threshold --values 0.7045654963945799 0.6
  ```

- Uitkomsten staan in `results_*.json` in deze map.

## Hoe de score werkt

Tijdlijn in blokjes van 0,1 s. Per handmatig gelabelde spreker wordt gekeken
welk deel van zijn/haar spreektijd gedekt wordt door één gekoppelde
pyannote-spreker (optimale 1-op-1-koppeling). Een spreker die pyannote nooit
als eigen spreker ziet, krijgt dus 0%. Overlap wordt mild geteld: als
pyannote twee sprekers actief heeft en één daarvan klopt, telt het blokje
als goed. Overlap-detectie zelf is geen instelbare parameter en wordt hier
niet gestraft. "Totaal juist" is gewogen naar spreektijd.

## Resultaten

Huidige instellingen van de pipeline: `min_cluster_size = 12`,
`threshold = 0.7046`, `method = centroid`, `segmentation.min_duration_off = 0.0`.

**`clustering.min_cluster_size`** (kleine clusters worden bij een grote
gevoegd):

| waarde | testaudio4: sprekers (echt 4) | testaudio4: totaal | testaudio2: sprekers (echt 2) | testaudio2: totaal |
|---|---|---|---|---|
| **12 (huidig)** | 2 | 81,0% | 2 | 78,0% |
| 10 | 2 | 81,0% | — | — |
| 8 | 4 | 83,2% | 2 | 78,0% |
| 6 | 6 | 75,7% | — | — |
| 3 | 6 | 75,7% | — | — |

**`clustering.threshold`** (hoe verschillend twee stemmen moeten klinken om
als verschillende sprekers te tellen):

| waarde | testaudio4: sprekers | testaudio4: totaal | testaudio2: sprekers | testaudio2: totaal |
|---|---|---|---|---|
| **0,70 (huidig)** | 2 | 81,0% | 2 | 78,0% |
| 0,60 | 2 | 81,0% | 3 | 57,7% |
| 0,50 | 2 | 66,5% | 3 | 57,7% |

## Conclusie

Tuning van deze instellingen geeft **geen aantoonbare, robuuste verbetering**.
Vooraf afgesproken criterium: minstens ongeveer +3 procentpunt op beide
fragmenten, zonder meer dan 1 verzonnen spreker erbij.

- `min_cluster_size = 8` is de enige instelling met winst: +2,2 punt op
  testaudio4 (vindt de verdwenen derde spreker, Emma, voor 97%), maar 0 op
  testaudio2. Dat haalt het criterium niet. De winst is bovendien wankel: een
  kleine stap verder (waarde 6) levert 6 sprekers op voor 4 echte en een
  lagere score. Ook is 8 gekozen door naar testaudio4 zelf te kijken, dus het
  getal is optimistisch.
- Verlagen van `threshold` maakt het slechter (testaudio2: -20 punt door een
  verzonnen derde spreker; testaudio4: -14,5 punt bij 0,50).
- In testaudio2 zit het probleem in een verkeerde samenvoeging (spreker B,
  7 s, wordt grotendeels bij A gezet). Geen van de geteste instellingen
  lost dat zonder nieuwe fouten op.
- De huidige instellingen (12 en 0,70) scoren op beide fragmenten het beste
  of gelijk. De productiepipeline is daarom **niet aangepast**.

## Beperkingen

- Twee korte fragmenten (30 s en 120 s) van dezelfde opnameserie. Emma heeft
  7,3 s spraak en spreker D is één zin van 0,8 s, dus uitkomsten over zulke
  sprekers zijn anekdotisch.
- Alleen losse instellingen getest, geen combinaties, en maar een paar
  waarden. `method` en `segmentation.min_duration_off` zijn niet getest.
- Overlap-detectie (rond 45% van de segmenten gevlagd) zit niet in de
  instelbare parameters en is dus met tuning niet te verbeteren.
- De voorgevulde tijden komen uit Whisper en zijn handmatig
  gecorrigeerd; ze zijn niet tot op de milliseconde nauwkeurig.

## Wat dit betekent voor de vervolgstappen

De beperking zit in de stemmen/opname zelf, niet in een instelling die met een
kleine test te vinden is. Realistische vervolgstappen: losse microfoons per
spreker bij toekomstige opnames, of een ander soort aanpak
(bijv. sprekerscheiding vóór diarisatie; een poging met
`pyannote/speech-separation-ami-1.0` liep vast op een
versie-incompatibiliteit tussen pyannote.audio 4.0.7 en speechbrain 1.1.1 en is
geparkeerd). Ondertussen blijft het systeem onzekerheid expliciet doorgeven
(`uncertain_assignment`, `overlap`, `docent_role_note`) in plaats van te gokken.

> **Vervolg:** de aanpak "sprekerscheiding/controle ná diarisatie" is
> uitgewerkt in [`../boundary_refinement`](../boundary_refinement/README.md):
> een verfijningsstap die pyannote's beurten per stuk spraak controleert met
> stem-embeddings. Die maakt een lagere `min_cluster_size` ook weer zinvol,
> omdat nep-sprekers achteraf worden samengevoegd.

---

# Controle van de verfijningsstap op de echte pipeline

De verfijningsstap (`src/speaker_boundaries.py`, standaard aan in
`diarization.py`) is opnieuw getoetst op de echte pipeline: echte
Whisper-transcripten, echt pyannote, en de handmatige ground truth uit deze
map. Dat kan met `Experiments/diarization/boundary_refinement/evaluate_refinement.py`.
De cijfers in de README van `boundary_refinement` komen uit een nabouw van
pyannote met de ground-truth-tijden als Whisper-grenzen en zijn dus
gunstiger dan de werkelijkheid.

Uitleg bij de kolommen: "tijdlijn" is dezelfde score als hierboven,
"segmenten goed" is het aandeel Whisper-segmenten met de juiste spreker (dat
is wat preprocessing en docentherkenning gebruiken), "gevaarlijke fouten" zijn
segmenten met de verkeerde spreker zonder overlap- of onzeker-vlag.

## testaudio2 en testaudio4 (dezelfde fragmenten waarop de regels zijn afgesteld)

| Fragment | Variant | tijdlijn | segmenten goed | gevaarlijke fouten | sprekers (echt) |
|---|---|---|---|---|---|
| testaudio2 | alleen pyannote, 12 | 78,0% | 68,4% | 4 | 2 (2) |
| testaudio2 | + refinement, 12 | 78,0% | 68,4% | 4 | 2 |
| testaudio2 | alleen pyannote, 8 | 78,0% | 68,4% | 4 | 2 |
| testaudio2 | + refinement, 8 | 78,0% | 68,4% | 4 | 2 |
| testaudio4 | alleen pyannote, 12 | 81,0% | 70,1% | 7 | 2 (4) |
| testaudio4 | + refinement, 12 | 82,1% | 70,1% | 6 | 2 |
| testaudio4 | alleen pyannote, 8 | 83,2% | 75,9% | 5 | 4 |
| testaudio4 | + refinement, 8 | 87,1% | 75,9% | 3 | 3 |

## final_testfragment (onafhankelijke toets)

Fragment van 312 s met veel rumoer; 137 regels gelabeld, 11 sprekers, waarvan
de docent 101 regels heeft en de meeste anderen één zin. Rumoer is niet als
aparte spreker gelabeld (alleen genoteerd). Dit fragment is niet gebruikt om
instellingen of regels te kiezen.

| Variant | tijdlijn | segmenten goed | gevaarlijke fouten | sprekers (echt 11) |
|---|---|---|---|---|
| alleen pyannote, 12 (huidig vóór de fix) | 68,7% | 73,7% | 7 | 2 |
| + refinement, 12 (huidige standaard) | 68,7% | 73,7% | 6 | 2 |
| alleen pyannote, 8 | 67,9% | 80,3% | 4 | 7 |
| + refinement, 8 | 67,8% | 77,4% | 5 | 4 |

## Conclusie

- **De verfijningsstap geeft geen aantoonbare verbetering.** Bij de
  standaardinstelling (12) is het verschil op alle drie de fragmenten nul of
  ongeveer één procentpunt. De grote winst bij testaudio4 met 8 (+6,1 punt
  tijdlijn ten opzichte van de situatie vóór de fix) komt niet terug op het
  onafhankelijke fragment, waar de stap met 8 juist iets slechter scoort dan
  pyannote alleen (77,4% tegen 80,3% op segmentniveau) doordat echte, kleine
  sprekers worden samengevoegd.
- Het criterium van minstens ongeveer +3 punt op alle fragmenten is niet gehaald.
- De stap staat standaard aan en voegt veel code en veel drempels toe
  (`speaker_boundaries.py` van ongeveer 700 regels, `BoundaryRefinementConfig`).
  Uitzetten kan met `--no-refine`.
- `min_cluster_size = 8` zonder refinement verdient een vervolgtest: op
  segmentniveau, wat downstream gebruikt wordt, is het beter op testaudio4
  (+5,8) en final_testfragment (+6,6) en gelijk op testaudio2, met minder
  gevaarlijke fouten (7 naar 5, 7 naar 4). Op de tijdlijn-score zag het er
  eerder niet beter uit (zie hierboven), dus de keuze van de maat telt. Het
  zijn kleine aantallen (19, 87 en 137 segmenten) en bij 8 komen er extra
  sprekers bij (7 in plaats van 2 op final_testfragment), waarvan een deel
  waarschijnlijk uit rumoer komt.

## Beperkingen

- Drie fragmenten van dezelfde klas en opnameserie; een verschil van 6 punten
  komt op final_testfragment neer op ongeveer 9 segmenten.
- Negen van de 11 gelabelde sprekers in final_testfragment zeggen één of twee
  zinnen en zijn voor pyannote niet te onderscheiden; hun spreker krijgt
  vrijwel altijd 0%. De tijdlijn-score wordt daardoor vooral door de docent
  bepaald.
- Op sommige regels van final_testfragment staat in de `note`-kolom dat het
  rumoer is of dat de labeler het niet zeker weet; de score gebruikt de
  `overlap`- en `note`-kolommen niet.
