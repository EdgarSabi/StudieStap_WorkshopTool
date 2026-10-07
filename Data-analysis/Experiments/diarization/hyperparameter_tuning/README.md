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
