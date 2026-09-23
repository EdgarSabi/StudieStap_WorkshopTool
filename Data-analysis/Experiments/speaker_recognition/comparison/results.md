# DOCENT vs OTHER — speaker-embedding experiment: resultaten

Verkennend experiment, losstaand van de productie-pipeline in `Data-analysis/src`.
Vraag: kan een speaker-embeddingmodel, op basis van één referentiefragment van de
docent (`testdocent.mp3`), per audiochunk onderscheiden of dat DOCENT of OTHER is?

## Gebruikte modellen

| Experiment | Model | Bron | Gated? |
|---|---|---|---|
| 1 — pyannote | `pyannote/wespeaker-voxceleb-resnet34-LM` | HuggingFace Hub | Nee — al lokaal gecached door eerdere diarizatieruns (het is het embeddingmodel dat `pyannote/speaker-diarization-3.1` zelf intern gebruikt) |
| 2 — SpeechBrain | `speechbrain/spkrec-ecapa-voxceleb` | HuggingFace Hub | Nee |

Beide zijn pretrained modellen; er is niets getraind of gefinetuned.

## Dependencies

- Alles draait in de bestaande venv `Data-analysis/src/.venv` (Python 3.14.7, torch 2.14.0+cpu, torchaudio 2.11.0). Geen CUDA, geen GPU nodig — alles op CPU, zelfde als de rest van de pipeline.
- Nieuw toegevoegd aan die venv (dry-run vooraf gecontroleerd: **geen** versieconflicten met faster-whisper/torch/torchaudio/pyannote/numpy/scipy die al voor de bestaande pipeline geïnstalleerd stonden):
  `speechbrain==1.1.1`, `soundfile`, `hyperpyyaml`, `sentencepiece`, `ruamel.yaml`, `cffi` (transitief).
  → Eén gedeelde venv was dus voldoende; een aparte environment was niet nodig.
- `pyannote.audio` (4.0.7) was al aanwezig, gebruikt voor experiment 1.
- `HF_TOKEN` uit `<repo-root>/.env` wordt hergebruikt (zelfde token als de bestaande diarizatie-pipeline). Voor SpeechBrain is dat niet strikt nodig (model is niet gated) maar voorkomt anonieme rate limits.
- Op Windows probeert SpeechBrain standaard modelbestanden te symlinken naar de cache-map, wat hier een privilege-fout gaf (`WinError 1314`, geen Developer Mode/admin). Opgelost door `local_strategy=LocalStrategy.COPY` mee te geven in `speechbrain_ecapa/test_teacher_recognition.py` — kopieert in plaats van symlinkt, geen systeeminstellingen aangepast.

## Testmethode

1. **Referentie**: `testdocent.mp3` (22.9s, alleen de docent) → geconverteerd naar 16 kHz mono wav → één teacher-embedding per model.
2. **Testchunks**: **hergebruikt**, niet opnieuw gegenereerd. De chunks zijn exact de ASR-segmenten uit de al bestaande
   `Data-local/processed/diarization/{testaudio1,testaudio2,testaudio5}_fragment_diarized.json`
   (die de bestaande pipeline al eerder produceerde), met hun bijbehorende `..._16k_mono.wav`.
   → 49 chunks in totaal (9 + 19 + 21), identiek voor beide experimenten, dus een eerlijke vergelijking.
3. Per chunk: audio slicen op start/end, embedding maken, **cosine similarity** tegen de teacher-embedding.
4. Distributie van de scores eerst bekeken (zie hieronder) vóór er een threshold gekozen is.
5. **Belangrijke kanttekening over "verwachte rol" in de tabel**: er is geen woord-voor-woord tijdgeannoteerde
   ground truth. De kolom "Verwachte rol" is met de hand afgeleid door de Whisper-tekst van elke chunk te
   vergelijken met de handmatige transcripties (`Data-local/raw/testaudio{1,2,5}_manual.txt`). Chunks die twee
   sprekers combineren (ASR-segmentatie liep niet gelijk met een sprekerwissel), buiten het bereik van de
   handmatige transcriptie vallen, of niet eenduidig te matchen waren, zijn gemarkeerd als **"onzeker"** en
   **niet meegeteld** in de indicatieve foutentelling verderop. Dit is dus geen formele evaluatieset — zie
   "Zwakke plekken" onderaan.

## Similarity-distributie (alle 49 chunks, vóór threshold-keuze)

| | n | min | p10 | p25 | mediaan | p75 | p90 | max | mean | std |
|---|---|---|---|---|---|---|---|---|---|---|
| pyannote | 49 | -0.182 | -0.011 | 0.094 | 0.249 | 0.532 | 0.634 | 0.802 | 0.306 | 0.268 |
| speechbrain | 49 | -0.042 | 0.043 | 0.133 | 0.269 | 0.474 | 0.622 | 0.774 | 0.307 | 0.226 |

Uitgesplitst naar mijn (indicatieve, zie hierboven) DOCENT/LEERLING-labels (20 DOCENT-chunks, 19 LEERLING-chunks;
de overige 10 "onzeker"/non-speech chunks buiten beschouwing):

| | DOCENT: min–max (mean) | OTHER: min–max (mean) | gat tussen medianen |
|---|---|---|---|
| pyannote | 0.094 – 0.802 (0.542) | -0.182 – 0.483 (0.123) | 0.572 vs 0.111 = **0.46** |
| speechbrain | 0.067 – 0.774 (0.487) | -0.011 – 0.393 (0.158) | 0.523 vs 0.144 = **0.38** |

Beide modellen laten een duidelijk zichtbare, maar niet perfect gescheiden, tweetoppige verdeling zien: de
meeste DOCENT-chunks clusteren rond 0.45–0.8, de meeste OTHER-chunks rond -0.2–0.3, met een overlappende
middenzone rond 0.3–0.45 waar vooral korte (~1s) uitingen in vallen.

## Gekozen threshold — EXPERIMENTELE instelling, geen bewezen betrouwbaar criterium

**Belangrijk, expliciet:** de onderstaande waarden zijn een experimentele instelling, gekozen door de
similarity-distributie op deze ene steekproef van 49 chunks visueel te inspecteren — géén gevalideerd of
bewezen betrouwbaar classificatiecriterium. Ze worden nergens automatisch toegepast om een bestaand
diarization-label te overschrijven; de CSV-output (`pyannote_teacher_similarity.csv` /
`speechbrain_teacher_similarity.csv`) bewaart per chunk altijd **drie aparte kolommen naast elkaar** —
`pipeline_speaker` (het oorspronkelijke diarization-label, ongewijzigd), `similarity` (de score), en
`prediction` (het eventuele nieuwe, op de threshold gebaseerde label) — plus een `agreement`/`conflict`-kolom
die alleen aangeeft OF de twee het met elkaar eens zijn, zonder ooit een winnaar te kiezen of een label te
overschrijven (zie `_common.compute_agreement()`). Elke rij met `conflict=True` moet gelezen worden als "deze
twee technieken spreken elkaar hier tegen", niet als "prediction is correct".

| Model | Threshold (experimenteel) | Rationale voor déze steekproef |
|---|---|---|
| pyannote | **0.35** | Ligt in het dal tussen de twee clusters. Bij dit punt: 3 van de 20 DOCENT-chunks worden gemist (FN), 1 van de 19 OTHER-chunks wordt fout als DOCENT gezien (FP) → 35/39 = **~90%** op de indicatieve labels. |
| speechbrain | **0.40** | Zelfde redenering. Bij dit punt: 5/20 FN, 0/19 FP → 34/39 = **~87%**. |

**Nogmaals: dit zijn géén formele accuracy-cijfers** — ze zijn berekend op 39 van de 49 chunks waarvoor ik zelf,
via tekstmatching met de handmatige transcripties, een rol heb toegekend. Ze zijn bedoeld om te laten zien dát
er een bruikbare scheiding zit, niet om een exact percentage te claimen, en zeker niet om de threshold als
"bewezen" te presenteren — een andere steekproef (andere docent, ander klaslokaal, andere microfoon) kan een
andere waarde nodig hebben. Met `--threshold` weggelaten draaien beide scripts alleen de distributie, zonder
enige DOCENT/OTHER-voorspelling te maken — dat is bewust de default.

Op déze steekproef geeft de threshold **14/49 conflicten** (pyannote) resp. **16/49** (speechbrain) tussen
`pipeline_speaker` en `prediction` — zie de CSV's voor de volledige lijst per rij.

**Welke fouten ontstaan** (op de indicatieve labels, thr pyannote=0.35 / speechbrain=0.40):
- Korte, op zichzelf staande uitingen van de docent worden het vaakst gemist (FN): *"Jawel."* (1.0s, pyannote 0.094, speechbrain 0.067), *"Wat voor probleem heeft-ie?"* (2.0s, beide ≈0.14–0.26), *"Oké, heel mooi."* (5.2s — lang genoeg, maar toch laag; mogelijk ruis/opname-artefact aan het begin van dat fragment).
- Eén overduidelijke FP bij pyannote: *"Dan staat-ie echt waar."* (leerling, 1.0s) scoort met 0.483 net boven de pyannote-threshold. Kan een genuine modelfout zijn, kan ook zijn dat mijn handmatige rol-koppeling hier mis is (de ASR-tekst is een parafrase en de exacte sprekerwissel binnen dat 1s-segment is niet zeker).
- SpeechBrain heeft in deze steekproef 0 FP maar meer FN dan pyannote — SpeechBrain is hier conservatiever (mist eerder een docent-chunk dan dat het een leerling-chunk verkeerd als docent bestempelt).

## Duur van de chunks — invloed op betrouwbaarheid

| Duurbucket | n (van 49) | pyannote mean sim | speechbrain mean sim |
|---|---|---|---|
| < 0.5s | 1 | 0.203 | 0.254 |
| 0.5–1s | 2 | 0.074 | 0.209 |
| > 1s | 46 | 0.318 | 0.313 |

**Deze dataset bevat bijna geen chunks korter dan 1s** (de bestaande ASR/diarizatie-segmentatie produceert hier
zelden zulke korte segmenten los) — met n=1 en n=2 is een harde uitspraak over de buckets < 0.5s en 0.5–1s niet
verantwoord. Wat wél zichtbaar is in de volledige tabel hieronder: **losse 1-woordsuitingen van ~1s**
("Jawel.", "Nee.", "Met zijn vrouw.") hebben bij beide modellen systematisch lagere/onzekerdere scores dan
langere uitingen van dezelfde spreker (>2s), ook als de rol correct is. Dat is consistent met de verwachting
dat zeer korte audio minder betrouwbaar te embedden is, maar met dit aantal voorbeelden is het een observatie,
geen onderbouwde conclusie.

## Volledige resultatentabel (alle 49 chunks)

*Zie voor de ruwe scores ook:*
`Data-local/processed/speaker_recognition/pyannote_teacher_similarity.csv` *en*
`Data-local/processed/speaker_recognition/speechbrain_teacher_similarity.csv`

| Fragment | Tijd | Tekst | Verwachte rol* | Pyannote sim | Pyannote voorsp. | SpeechBrain sim | SpeechBrain voorsp. | Opmerking |
|---|---|---|---|---|---|---|---|---|
| audio1 | 0.0-2.08s | Dit is mijn presentatie. | LEERLING | 0.0224 | OTHER | 0.051 | OTHER | |
| audio1 | 2.24-3.96s | APPLAUS | N/A (applaus) | -0.1811 | OTHER | -0.0419 | OTHER | geen betrouwbare handmatige rol |
| audio1 | 4.12-9.36s | Oké, heel mooi. | DOCENT | 0.2495 | OTHER | 0.2838 | OTHER | pyannote fout; speechbrain fout |
| audio1 | 9.52-11.64s | Dit ben jij. Dit ben ik. | onzeker (gemengd) | 0.2444 | OTHER | 0.334 | OTHER | geen betrouwbare handmatige rol |
| audio1 | 11.8-15.64s | Zit er ook nog in je karaktereigens... | DOCENT | 0.5273 | DOCENT | 0.5274 | DOCENT | |
| audio1 | 15.8-20.28s | Nee. Dit is een heel originele mani... | onzeker (gemengd) | 0.5317 | DOCENT | 0.473 | DOCENT | geen betrouwbare handmatige rol |
| audio1 | 20.44-24.48s | Er zitten alle ingrediënten in. Wie... | onzeker (gemengd) | 0.4473 | DOCENT | 0.4039 | DOCENT | geen betrouwbare handmatige rol |
| audio1 | 24.64-29.52s | Floris, wil jij een stukje van Maxi... | DOCENT (gok) | 0.574 | DOCENT | 0.5938 | DOCENT | |
| audio1 | 29.52-30.56s | Bitter. | LEERLING (gok) | 0.203 | OTHER | 0.2535 | OTHER | kort (0.46s) |
| audio2 | 0.0-2.0s | Vier, Rick. Zegt u het maar. | DOCENT | 0.5694 | DOCENT | 0.6269 | DOCENT | |
| audio2 | 2.0-4.0s | Ja, kijk maar even in je schrift op... | DOCENT | 0.5779 | DOCENT | 0.4184 | DOCENT | |
| audio2 | 4.0-5.0s | Ruud heeft een brommer. | LEERLING | 0.1229 | OTHER | 0.0488 | OTHER | |
| audio2 | 5.0-7.0s | De tekst gaat toch niet over bromme... | DOCENT | 0.5613 | DOCENT | 0.5195 | DOCENT | |
| audio2 | 7.0-9.0s | Nee, maar het gaat ook niet om de b... | LEERLING | 0.1427 | OTHER | 0.2834 | OTHER | |
| audio2 | 9.0-11.0s | Maar Ruud heeft een probleem, dat i... | DOCENT | 0.6251 | DOCENT | 0.5591 | DOCENT | |
| audio2 | 11.0-13.0s | Wat voor probleem heeft-ie? | DOCENT | 0.2613 | OTHER | 0.1421 | OTHER | pyannote fout; speechbrain fout |
| audio2 | 13.0-14.0s | Met zijn vrouw. | LEERLING | 0.0017 | OTHER | 0.0699 | OTHER | |
| audio2 | 14.0-15.0s | Nee, klopt niet. | DOCENT | 0.4175 | DOCENT | 0.1947 | OTHER | speechbrain fout |
| audio2 | 15.0-16.0s | Ik bedoel, met zijn hond. | LEERLING | 0.281 | OTHER | 0.1436 | OTHER | |
| audio2 | 16.0-17.0s | Ja, je bent gewoon verzinnen, of niet? | DOCENT | 0.4648 | DOCENT | 0.4705 | DOCENT | |
| audio2 | 17.0-18.0s | Nee. | LEERLING | 0.2189 | OTHER | 0.1332 | OTHER | |
| audio2 | 18.0-19.0s | Jawel. | DOCENT | 0.0943 | OTHER | 0.0666 | OTHER | pyannote fout; speechbrain fout |
| audio2 | 19.0-20.0s | Dan staat-ie echt waar. | LEERLING | 0.4826 | DOCENT | 0.3928 | OTHER | pyannote fout |
| audio2 | 20.0-21.0s | Ja, het staat in jouw schrift. | DOCENT | 0.5987 | DOCENT | 0.2874 | OTHER | speechbrain fout |
| audio2 | 21.0-23.0s | Misschien staat het niet in zijn sc... | DOCENT | 0.4897 | DOCENT | 0.4741 | DOCENT | |
| audio2 | 23.0-25.0s | Je ziet je ogen heen en weer gaan. | DOCENT | 0.5319 | DOCENT | 0.4531 | DOCENT | |
| audio2 | 25.0-28.0s | Dus ik denk, nou gaat je hoofd heen... | DOCENT | 0.6083 | DOCENT | 0.571 | DOCENT | |
| audio2 | 28.0-30.0s | Dus ja, ja. | onzeker | 0.4989 | DOCENT | 0.4832 | DOCENT | geen betrouwbare handmatige rol |
| audio5 | 0.82-3.26s | Oswaldo is jouw beste vriend, hé? O... | DOCENT | 0.7876 | DOCENT | 0.7065 | DOCENT | |
| audio5 | 3.38-4.38s | Hier in de klas, ja. | DOCENT | 0.6683 | DOCENT | 0.6211 | DOCENT | |
| audio5 | 4.5-8.98s | Stel je nou voor dat Oswaldo homo is. | DOCENT | 0.8018 | DOCENT | 0.7737 | DOCENT | |
| audio5 | 9.1-10.82s | Zou dat invloed hebben op je vriend... | DOCENT | 0.7157 | DOCENT | 0.7156 | DOCENT | |
| audio5 | 10.94-12.54s | Jazeker. Dat zou wel invloed hebben. | LEERLING | 0.1108 | OTHER | 0.2688 | OTHER | |
| audio5 | 12.66-13.66s | Wat bedoel je? | LEERLING | 0.0535 | OTHER | 0.2032 | OTHER | |
| audio5 | 13.78-14.74s | Gewoon, toch? | LEERLING | -0.1816 | OTHER | -0.0105 | OTHER | kort (0.96s) |
| audio5 | 14.86-17.22s | Dat heeft invloed op onze vriendschap. | LEERLING | 0.2412 | OTHER | 0.2455 | OTHER | |
| audio5 | 17.34-20.54s | Als ik zeg dat ik homo ben, dan ga ... | LEERLING | 0.0989 | OTHER | 0.1368 | OTHER | |
| audio5 | 20.66-22.82s | Dan komt het wel op neer, ja. | LEERLING | -0.0626 | OTHER | 0.0802 | OTHER | |
| audio5 | 22.94-25.14s | Wat is er met me huis geweest? | LEERLING | 0.1655 | OTHER | 0.2286 | OTHER | |
| audio5 | 25.26-27.82s | Als jij nu zegt dat je homo bent, d... | LEERLING | 0.2441 | OTHER | 0.2276 | OTHER | |
| audio5 | 28.14-31.22s | Omdat ik met jou nu, Safi, zeg nu, ... | LEERLING | 0.0558 | OTHER | 0.005 | OTHER | |
| audio5 | 31.34-32.34s | Kere! | onzeker | -0.0729 | OTHER | 0.1359 | OTHER | geen betrouwbare handmatige rol |
| audio5 | 32.46-33.46s | Kere! | onzeker | 0.014 | OTHER | 0.0291 | OTHER | geen betrouwbare handmatige rol |
| audio5 | 33.58-35.94s | Dat krijgen we dan nooit doen! | onzeker | -0.1315 | OTHER | 0.046 | OTHER | geen betrouwbare handmatige rol |
| audio5 | 36.06-38.1s | Maar dat ligt gewoon aan jou, niet ... | LEERLING | 0.0646 | OTHER | 0.149 | OTHER | |
| audio5 | 38.22-40.74s | Nee, dan ligt het op dat moment aan... | LEERLING | 0.0709 | OTHER | 0.0944 | OTHER | |
| audio5 | 40.86-42.82s | Dat ligt gewoon aan jou, want jij b... | onzeker | 0.1301 | OTHER | 0.0325 | OTHER | geen betrouwbare handmatige rol |
| audio5 | 42.94-44.98s | Wacht even, wat is er aan de hand? | DOCENT | 0.7121 | DOCENT | 0.732 | DOCENT | |
| audio5 | 45.1-46.1s | Hoe is het een facky... | onzeker | 0.329 | OTHER | 0.4295 | DOCENT | kort (0.89s); geen betrouwbare handmatige rol |

\* Handmatig afgeleid door ASR-tekst te matchen met `Data-local/raw/testaudio{1,2,5}_manual.txt`. "onzeker" =
segment combineert twee sprekers, valt buiten de handmatige transcriptie, of tekst is te onduidelijk/ASR-garbled
om te matchen. "(gok)" = buiten het bereik van de handmatige transcriptie, rol ingeschat op basis van context.

## Beantwoording van de onderzoeksvragen

**1. Vormt de docent een duidelijk herkenbare similarity-cluster?**
Ja, redelijk duidelijk: bij beide modellen liggen de meeste DOCENT-chunks (langer dan ~1.5s) tussen 0.45 en
0.80, ver boven de meeste OTHER-scores. `testaudio5` (de docent in een langere alleenspraak-passage) geeft het
schoonste cluster (0.67–0.80). De cluster is minder scherp voor korte, geïsoleerde docent-uitingen.

**2. Zijn OTHER-speakers duidelijk lager in similarity?**
Ja, over het geheel wel: OTHER-mediaan ligt rond 0.11–0.14 tegen een DOCENT-mediaan van 0.52–0.57. Er zijn
enkele uitschieters naar boven bij OTHER (met name korte, dubbelzinnige segmenten), maar de meerderheid zit
duidelijk lager.

**3. Welk model scheidt DOCENT en OTHER het duidelijkst?**
**Pyannote** (`wespeaker-voxceleb-resnet34-LM`) had in deze steekproef het grootste gat tussen de
DOCENT- en OTHER-medianen (0.46 vs 0.38 voor SpeechBrain) en de hoogste indicatieve "accuracy" (~90% vs ~87%)
bij een threshold in het dal tussen de clusters. SpeechBrain was conservatiever: minder false positives
(0 vs 1) maar meer false negatives (5 vs 3). Het verschil is met 49 chunks te klein om hard te stellen dat
pyannote structureel beter is — maar in deze test presteerde het net iets scherper.

**4. Gevoeligheid voor ruis / overlap / korte uitingen?**
- *Korte uitingen (~1s, losse woorden)*: duidelijk de zwakste categorie bij beide modellen — dit is waar
  bijna alle fout-classificaties vandaan komen (zie tabel: "Jawel.", "Nee.", "Wat voor probleem heeft-ie?").
- *Overlap*: de bestaande diarizatie-JSON markeert sommige segmenten al als `overlap=true` (twee sprekers
  door elkaar); dat is in dit experiment niet apart uitgesplitst, maar de gemengde/"onzeker" segmenten in de
  tabel (waar Whisper twee sprekerbeurten in één segment plakte) laten zien dat een chunk met twee sprekers
  een vaag, tussen-in similarity-signaal geeft — logisch, de embedding vermengt dan letterlijk twee stemmen.
- *Achtergrondruis / applaus*: het "APPLAUS"-segment (geen spraak) gaf bij beide modellen een lage/negatieve
  score, wat op zich correct gedrag is (het is inderdaad geen docent), maar laat wel zien dat dit soort
  non-speech chunks eigenlijk vooraf gefilterd zouden moeten worden — niet aan het similarity-model overlaten.

**5. Eenvoudiger/bruikbaarder dan volledige diarizatie?**
Voor de specifieke vraag "is dit de docent, ja of nee" lijkt dit een lichter en gerichter alternatief:
- **Voordeel**: geen sprekertelling/clustering nodig, geen aparte behandeling van "hoeveel leerlingen zijn
  er" — precies wat gevraagd was. Op `testaudio2` bleek dit zelfs een meerwaarde: de bestaande
  diarizatie-pipeline labelde daar *alle* 19 segmenten als één spreker (`MAIN_SPEAKER`), terwijl de
  handmatige transcriptie duidelijk afwisselend docent/leerling is — de embedding-similarity ziet dat
  onderscheid per chunk wél (zie tabel, sim wisselt chunk voor chunk tussen ~0.5-0.6 en ~0.0-0.3).
- **Nadeel**: dit experiment classificeert per *bestaande* chunk — het doet zelf geen segmentatie. Zonder
  chunks van een aparte bron (ASR-segmenten, VAD, of turn-detectie) is er niets om embeddings op te maken.
  Volledige diarizatie blijft dus nodig zolang je *ook* wilt weten wanneer sprekerwissels plaatsvinden, of als
  er geen bruikbare referentie-audio van de docent is (bij deze aanpak moet je vooraf al weten wie de docent
  is en een schoon fragment van diegene hebben — dat is een aanname die volledige diarizatie niet maakt).
- Kortom: als *enige* vraag "docent of niet" is, en er al chunks + een schone referentie zijn, is dit een
  bruikbare, goedkopere aanvulling — geen vervanging van diarizatie, wel een mogelijke verbetering/correctie
  erbovenop (zoals het testaudio2-voorbeeld laat zien).

## Zwakke plekken van dit experiment

- **Geen formele ground truth.** De "verwachte rol"-kolom is met de hand afgeleid uit tekstvergelijking met de
  handmatige transcripties, niet uit tijdgeannoteerde labels. 10 van de 49 chunks zijn als "onzeker" gemarkeerd
  en niet meegeteld. De gerapporteerde ~87-90% is dus indicatief, geen accuracy/DER-claim.
- **Kleine steekproef.** 49 chunks, 3 fragmenten, 1 docent, een handvol leerlingen. Te klein om een threshold
  hard aan te bevelen voor productiegebruik.
- **Bijna geen echt korte chunks (<1s)** in deze data — de vraag "hoe gevoelig voor korte uitingen" kon daarom
  alleen kwalitatief (via ~1s-uitingen) beantwoord worden, niet met een echte sub-buckets-vergelijking.
- **Eén enkele referentie-opname.** Eén stemtoestand van de docent (toon, volume, opnamecondities). Geen
  robuustheidstest tegen bijvoorbeeld een docent die fluistert, roept, of via een andere microfoon spreekt.
- **Threshold is per model en per dataset gekozen op dezelfde data als waarop hij getest is** (geen aparte
  train/val-split) — dat is prima voor dit verkennende stadium, maar niet geschikt om zo te presenteren als
  "de" threshold voor productie.
- Beide modellen zijn getraind op (voornamelijk Engelstalige) VoxCeleb-data, niet op Nederlandse klasgesprekken
  — dat kan meespelen in de ruis die we zien, vooral bij korte/emotionele uitingen.

## Voorlopige conclusie

Met één schoon referentiefragment van de docent geven zowel pyannote (`wespeaker-voxceleb-resnet34-LM`) als
SpeechBrain (`spkrec-ecapa-voxceleb`) een bruikbaar, zij het niet perfect, DOCENT/OTHER-signaal via cosine
similarity — vooral op chunks langer dan ~1.5–2s. Pyannote scheidt de twee klassen in deze test iets scherper.
De grootste zwakte zit bij korte, geïsoleerde uitingen (~1s), niet bij ruis of het aantal "andere" sprekers.
Dit is geen vervanging voor de bestaande diarizatie-pipeline (die nog steeds nodig is om chunks/sprekerwissels
te vinden), maar kan er wel een nuttige, goedkope check bovenop zijn — het testaudio2-voorbeeld laat zien dat
het zelfs iets kan oppikken wat de huidige turn-based diarizatie daar mist. Voor een volgende stap zou een
grotere, met de hand tijdgeannoteerde testset nodig zijn om een threshold en een "eenvoudiger dan diarizatie"-
aanpak serieus te onderbouwen.
