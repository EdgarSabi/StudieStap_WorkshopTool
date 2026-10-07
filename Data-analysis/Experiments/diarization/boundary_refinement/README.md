# Sprekergrenzen verfijnen na pyannote (stap 2b)

Dit experiment hoort bij een nieuwe stap in de pipeline:
[`src/speaker_boundaries.py`](../../../src/speaker_boundaries.py). Die stap
draait automatisch in `diarization.py`, direct na pyannote en vóór het
koppelen aan de transcriptsegmenten. Uitzetten kan met `--no-refine`, zodat je
altijd met het oude gedrag kunt vergelijken.

## Waarom

Het hyperparameter-experiment liet zien dat geen enkele instelling van
pyannote de bekende problemen robuust oplost. Om te snappen wáár het misgaat
heb ik de pyannote-pipeline nagebouwd met precies dezelfde modelgewichten
(zie `onnx_reproductie/`). Die nabouw komt op de bekende fragmenten bijna
exact uit op de echte pyannote-scores: testaudio2 78,3% (echt 78,0%),
testaudio4 81,0% met spreker C en D volledig kwijt (echt ook 81,0%, ook C en D
kwijt). Daarmee kon ik in de tussenstappen kijken.

Wat daaruit bleek:

- **Het segmentatiemodel hoort de wissel soms gewoon niet.** In testaudio2 ziet
  pyannote tussen 9 en 17 seconden één doorlopende spreker, terwijl leerling B
  daar twee keer iets zegt. Geen clustering-instelling kan een wissel
  terugvinden die het segmentatiemodel nooit gezien heeft. Dat verklaart
  waarom tuning niets deed voor testaudio2.
- **Een stem-embedding van precies dat Whisper-segment ziet het verschil wél.**
  "Met zijn vrouw." (13–14 s) heeft een cosine-similarity van ongeveer 0,1 met
  de docent, terwijl stukken van de docent onderling rond 0,5–0,6 zitten.
- **Vaste schuivende vensters werken slecht in een klas.** Beurten van rond
  de één seconde zijn heel normaal, dus een venster van 1,5 s bevat bijna
  altijd ook een stukje van de vorige of volgende spreker. Mijn eerste versie
  (Viterbi over schuivende vensters) maakte daardoor zelfs een *perfecte*
  diarisatie slechter. Die aanpak is weggegooid.
- **De docent klinkt heel consistent, leerlingen niet.** De docent zit dicht
  bij de microfoon en praat veel; leerlingen zijn ver weg, kort en zitten in
  het rumoer. Hun stukken lijken nauwelijks op elkaar (0,1–0,4). Je herkent
  een leerling dus betrouwbaarder aan "dit past niet bij de docent" dan aan
  "dit lijkt op leerling B".

## Hoe de stap werkt

De tijdlijn wordt geknipt op elke Whisper-segmentgrens en elke
pyannote-grens. Elk stuk met één spreker is een *eenheid*, en elke eenheid van
minstens 0,5 s krijgt een embedding van precies dat stuk audio (dus zonder
buren erbij). Per spreker wordt een profiel gemaakt, plus een maat voor hoe
goed eigen stukken normaal bij dat profiel passen (mediaan en spreiding, per
spreker). Daarna:

1. **Samenvoegen** – twee clusters die dezelfde stem blijken te zijn worden
   één spreker. Dit vangt de nep-sprekers op die je krijgt als je
   `min_cluster_size` verlaagt.
2. **Omlabelen** – een eenheid (≥ 0,8 s) die een duidelijke uitschieter is voor
   haar eigen spreker en wél past bij een andere, wordt omgezet. Dat zijn de
   gemiste sprekerwissels.
3. **Splitsen** – lange eenheden worden op een stilte geprobeerd te knippen
   als de twee helften bij verschillende sprekers horen.
4. **Nieuwe spreker** – stukken die bij niemand passen en onderling op
   elkaar lijken worden een eigen spreker (`REFINED_NEW_n`).
5. **Onzekerheid** – elke eenheid is "duidelijk" of "onduidelijk". Een
   transcriptsegment dat vooral op onduidelijke stukken valt wordt
   `uncertain_assignment`, zodat docentherkenning er niet op gaat gokken.

Alle drempels staan in `BoundaryRefinementConfig` in `config.py` en zijn per
spreker relatief (hoeveel wijkt dit af van wat normaal is voor díe spreker),
niet in vaste cosine-waarden. Alles wat de stap verandert staat met reden in
de output-JSON onder `diarization.boundary_refinement.changes`, dus je kunt
elke wijziging terugluisteren.

## Resultaten (op de nabouw)

Tijdlijn-score is dezelfde maat als in het hyperparameter-experiment.
Whisper-grenzen zijn benaderd met de grenzen uit de ground truth plus ±0,15 s
ruis.

| Fragment | min_cluster_size | Alleen pyannote | + refinement | Wat er verandert |
|---|---|---|---|---|
| testaudio2 | 12 | 78,3% (B 28,6%) | **84,0%** (B 55,7%) | 2 stukken van B teruggezet |
| testaudio4 | 12 | 81,0% (2 sprekers) | **81,9%** | 1 stuk van B teruggezet; C blijft weg |
| testaudio4 | 8 | 73,3% (7 sprekers) | **80,1%** (5 sprekers) | 2 nep-sprekers samengevoegd, C 98,6% gevonden |
| testaudio2 perfect* | – | 100% | 97,0% | 1 twijfelgeval ("Jawel.") omgezet |
| testaudio4 perfect* | – | 100% | 100% | niets |

\* *perfect* = de ground truth zelf als invoer. Dit checkt dat de stap goede
diarisatie niet kapotmaakt.

Op segmentniveau (wat preprocessing en docentherkenning echt gebruiken):

| Fragment | Instelling | Segmenten goed | Fout én niet gevlagd |
|---|---|---|---|
| testaudio2 | pyannote | 0,79 | 4 |
| testaudio2 | + refinement | **0,89** | **2** |
| testaudio4 | pyannote (12) | 0,70 | 16 |
| testaudio4 | + refinement (12) | 0,70 | 16 |
| testaudio4 | + refinement (8) | **0,75** | **13** |

Op drie fragmenten zonder ground truth (testaudio1_fragment,
testaudio5_fragment en de volledige testaudio2 van 7,5 minuut) gedraagt de
stap zich terughoudend: 0 tot 5 seconden omgelabeld, steeds met een
duidelijke reden (similarity rond 0 met de eigen spreker, 0,3–0,6 met de
nieuwe). Bij testaudio5 worden 5 pyannote-sprekers er 3, wat overeenkomt met
wat community-1 eerder vond. Rekentijd: ongeveer 25 s voor 7,5 minuut audio op
CPU.

## Wat dit wel en niet oplost

| Probleem uit de lijst | Status |
|---|---|
| Gemiste sprekerwissels (testaudio2) | **Deels opgelost.** B gaat van 29% naar 56%. Werkt als Whisper of pyannote een grens op die plek heeft, of als er een stilte is binnen een lang stuk. |
| Korte sprekers verdwijnen | **Opgelost in combinatie met `--min-cluster-size 8`.** Emma (C) wordt dan voor 99% gevonden. Bij 12 blijft ze weg: haar stukken wijken dan niet duidelijk genoeg af van de bestaande sprekers. |
| Over-segmentatie bij lagere min_cluster_size | **Grotendeels opgelost.** Van 7 naar 5 sprekers bij testaudio4 (echt: 4). |
| Overlap | **Niet opgelost.** Overlap-stukken worden bewust niet aangeraakt. Daarvoor is echte bronscheiding nodig. |
| uncertain_assignment / docentherkenning op foute beurten | **Beter.** Minder beurten waarin twee sprekers ongemerkt zijn samengevoegd, en twijfel komt nu ook uit de stemvergelijking. |
| Woordniveau-attributie heeft een grens nodig | **Beter.** Er zijn nu meer grenzen om op te koppelen. |
| Rumoer / afstandsmicrofoon | **Niet opgelost.** Wel worden stukken die nergens op lijken nu als onduidelijk gemarkeerd in plaats van stil bij de docent gezet. |

## Belangrijke kanttekeningen

- **De cijfers komen van de nabouw, niet van echte pyannote.** In deze
  omgeving was HuggingFace niet bereikbaar. De nabouw gebruikt dezelfde
  gewichten en komt op dezelfde basisscores uit, maar bij
  `min_cluster_size=8` wijkt hij af (7 sprekers, echte pyannote 4). Draai
  daarom `evaluate_refinement.py` (hieronder) met de echte pipeline voordat je
  conclusies trekt.
- **De drempels zijn op testaudio2 en testaudio4 afgesteld**, dezelfde twee
  fragmenten waarop gescoord is. De cijfers zijn dus optimistisch. Een eerlijke
  check is een nieuw fragment met ground truth dat niet gebruikt is om af te
  stellen. Het hyperparameter-README noemt testaudio6 daarvoor.
- `min_cluster_size` staat standaard nog op pyannote's eigen 12. Op deze twee
  fragmenten scoort 8 + refinement op segmentniveau beter. Ik heb de standaard
  bewust niet veranderd zonder controle op echte pyannote.

## Zelf draaien

Met de echte pipeline (vanuit `Data-analysis/src`, met HF_TOKEN):

```
.venv\Scripts\python.exe ..\Experiments\diarization\boundary_refinement\evaluate_refinement.py testaudio2_fragment testaudio4_fragment --min-cluster-size 12 8
```

Dit draait pyannote met en zonder refinement, scoort tegen de ground truth
(tijdlijn én segmentniveau) en schrijft `results_<fragment>.json` in deze map.
Er moet een transcript in `Data-local/processed/<fragment>.json` staan;
zonder transcript werkt de refinement alleen op pyannote-grenzen en dat is
duidelijk zwakker (testaudio2: 80,7% in plaats van 84,0%).

De gewone pipeline:

```
.venv\Scripts\python.exe run_docent_pipeline.py testaudio2_fragment.mp3 --force
.venv\Scripts\python.exe run_docent_pipeline.py testaudio4_fragment.mp3 --min-cluster-size 8 --force
.venv\Scripts\python.exe run_docent_pipeline.py testaudio2_fragment.mp3 --no-refine --force   # oud gedrag
```

Om de cijfers van de nabouw te reproduceren zonder HF-token: zie
`onnx_reproductie/reproduce_local_results.py`.

## Volgende stappen

1. `evaluate_refinement.py` draaien op de echte pyannote voor testaudio2 en 4.
2. Ground truth maken voor testaudio6 en daar controleren zonder iets bij te
   stellen. Pas daarna beslissen of `min_cluster_size=8` de standaard wordt.
3. Voor overlap blijft bronscheiding de logische volgende stap.
   `pyannote/speech-separation-ami-1.0` liep eerder vast op een
   versieconflict; dat is los van deze stap nog steeds open.
