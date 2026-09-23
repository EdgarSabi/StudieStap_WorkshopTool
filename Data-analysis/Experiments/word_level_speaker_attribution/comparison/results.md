# Fase 4 — word-level speaker attribution: resultaten

Vraag: kunnen de bestaande Faster-Whisper- en pyannote-componenten
gecombineerd worden om woorden nauwkeuriger aan DOCENT/OTHER te koppelen,
zonder WhisperX volledig te adopteren? Vergeleken op dezelfde 3
testfragmenten als de eerdere diarizatie- en speaker-recognition-experimenten:
`testaudio1_fragment`, `testaudio2_fragment`, `testaudio5_fragment`.

## Drie aparte technieken, drie aparte vragen

Zoals gevraagd expliciet uit elkaar gehouden — ze beantwoorden niet dezelfde
vraag en hun resultaten mogen niet worden samengevoegd tot één score:

1. **Sprekerwisselingen detecteren** — het pyannote-diarizationmodel zelf
   (ongewijzigd, `speaker-diarization-3.1`). Bepaalt de turn-grenzen die
   Stap 3 gebruikt. Als dit model een wissel niet ziet, kan geen van de
   volgende stappen die alsnog verzinnen.
2. **Woorden aan sprekers koppelen** — Stap 3: dezelfde tijd-overlap-
   geometrie als het bestaande `diarization/assign.py`, nu per **woord**
   (via `word_timestamps=True`, Stap 2) in plaats van per ASR-segment.
3. **De docent identificeren** — Stap 4: cosine similarity tussen een
   spraakstuk en de `testdocent.mp3`-referentie-embedding
   (`pyannote/wespeaker-voxceleb-resnet34-LM`, hergebruikt uit
   `speaker_recognition/`). Onafhankelijk van welk diarization-label een
   stuk audio kreeg.

## Modellen & dependencies

| | |
|---|---|
| ASR | faster-whisper `medium`, taal `nl`, `word_timestamps=True` — zelfde model als de baseline gebruikte voor deze fragmenten, zelfde overige instellingen (zie Stap 2) |
| Diarization | `pyannote/speaker-diarization-3.1` — ongewijzigd, **niet** vervangen door community-1 of iets anders (expliciet buiten scope) |
| Speaker recognition | `pyannote/wespeaker-voxceleb-resnet34-LM` — hergebruikt uit `Experiments/speaker_recognition/` |
| Nieuwe dependencies | **geen** — alles draait in de bestaande `Data-analysis/src/.venv` |
| Wijzigingen aan bestaande code | **geen** — `transcription/engine.py`, `models/schema.py`, `diarization/*`, `preprocessing/*` allemaal ongewijzigd. Deze scripts importeren en hergebruiken ze read-only. |

## Stap 2 — hoe betrouwbaar zijn de word_timestamps?

`TranscriptionConfig.word_timestamps` bestond al als vlag en werd al
doorgegeven aan faster-whisper, maar `Segment.words` werd nergens gelezen —
`TranscriptSegment` heeft geen `words`-veld. Dit experiment leest en bewaart
die data (in een eigen JSON, `schema.py` blijft ongewijzigd) en checkt de
betrouwbaarheid ervan:

| Fragment | Woorden | Gem. duur | Gem. prob. | Prob. < 0.5 | Nul-duur woorden | Niet-monotoon | Buiten segmentgrenzen |
|---|---|---|---|---|---|---|---|
| testaudio1 | 65 | 0.266s | 0.807 | 11 (17%) | 3 | 0 | 0 |
| testaudio2 | 118 | 0.190s | 0.817 | 14 (12%) | 3 | 0 | 0 |
| testaudio5 | 136 | 0.225s | 0.776 | 25 (18%) | 6 | 0 | 0 |

- **Nooit niet-monotoon of buiten de segmentgrenzen** — de timestamps zelf
  zijn intern consistent.
- **~12-18% van de woorden heeft een per-woord probability < 0.5** — dit is
  faster-whisper's eigen ingebouwde confidence-signaal, en is nu voor het
  eerst zichtbaar/bruikbaar (voorheen impliciet weggegooid). Bruikbaar als
  extra kwaliteitsfilter, niet in deze fase al toegepast.
- **Een handvol woorden per fragment (3-6) heeft duur = 0** — een bekende
  faster-whisper-eigenaardigheid (DTW-alignment die soms samenvalt op één
  tijdstip). Stap 3 behandelt zo'n woord altijd als onzeker (zie daar), nooit
  als een stille misser.
- **Belangrijke kanttekening: `word_timestamps=True` verandert soms ook de
  ASR-output zelf, niet alleen de timestamps.** testaudio1 en testaudio2
  kregen exact hetzelfde aantal segmenten (9 resp. 19) als de baseline, maar
  testaudio1's laatste segment veranderde van tekst ("Bitter." →
  "Je zit bitter in..."). **testaudio5 kreeg 18 segmenten in plaats van de
  baseline's 21** — een andere VAD-segmentatie-uitkomst. Dit is dus **niet**
  een drop-in vlag zonder enig neveneffect; "of bestaande functionaliteit
  behouden blijft" is het antwoord: grotendeels wel (zelfde model, zelfde
  hoofd-inhoud), maar niet garandeerd byte-identiek — een reëel punt om mee
  te wegen bij eventuele integratie.
- Runtime: 23.2s / 44.0s / 48.6s (t1/t2/t5) — vergelijkbare orde van grootte
  als de baseline-transcriptie van dezelfde fragmenten (21.3s / 36.5s /
  89.5s; testaudio5's baseline-run was ditmaal duidelijk trager, vermoedelijk
  run-to-run variatie op dit CPU-only systeem, geen systematisch WhisperX-
  achtig overhead).

## Stap 3 — word-level attribution: wat gebeurt er in de probleemgevallen?

Dezelfde tijd-overlap-geometrie als `assign.py`, nu per woord. Nooit een
gok bij tegenstrijdige informatie: `uncertain=True` + een `note` die zegt
waarom (`no_overlapping_turn`, `zero_duration_word(_no_unique_turn)`,
`low_coverage`, `ambiguous_margin`).

| Fragment | Turns/raw speakers | Woorden | Onzeker | Overlap | Niet toegewezen | ASR-segmenten met >1 spreker (los / zeker) |
|---|---|---|---|---|---|---|
| testaudio1 | 21 turns / 3 | 65 | 6 (9%) | 5 (8%) | 1 | 4/9 los, **3/9 zeker** |
| testaudio2 | 8 turns / 2 | 118 | 22 (19%) | 21 (18%) | 0 | **0/19** |
| testaudio5 | 23 turns / 5 | 136 | 25 (18%) | 18 (13%) | 1 | 3/18 los, 1/18 zeker |

**Wat er gebeurt bij de vier gestelde scenario's:**

- **Eén ASR-segment met twee sprekers** — als de onderliggende
  diarization-turns wél een grens in dat tijdsinterval hebben, splitst
  Stap 3 het segment correct op woordniveau (zie AUDIO1 hieronder — het
  kernresultaat van dit experiment). Als de diarization-turns die grens
  **niet** hebben, kán Stap 3 hem niet vinden: elk woord overlapt dan met
  precies dezelfde ene turn, dus met 100% coverage — **niet onzeker**, maar
  wel mogelijk fout (zie AUDIO2 hieronder: dit is de belangrijkste,
  contra-intuïtieve bevinding van deze stap).
- **Diarization mist een sprekerwissel** — zie vorige punt: woordniveau-
  koppeling kan een wissel die de diarization zelf niet ziet niet
  reconstrueren. Het probleem verplaatst zich niet op, het blijft bij de
  bron (het diarizationmodel), exact zoals de eerdere WhisperX-vergelijking
  al concludeerde.
- **Woorden overlappen** (crosstalk) — 8-18% van de woorden krijgt
  `overlap=True` (een tweede spreker dekt ook een relevant deel van het
  woord). Bij zeer korte woorden (~0.1-0.2s) is dat een aanzienlijk aandeel
  van de woordduur al genoeg voor die vlag — zie testaudio5's voorbeeld
  hieronder.
- **Een woord niet betrouwbaar toe te wijzen** — 9-19% van de woorden wordt
  `uncertain`. Dat is **hoger** dan het aandeel onzekere/overlap-segmenten
  op segmentniveau in de baseline (testaudio1: 5/9 segmenten onzeker vs.
  6/65 woorden onzeker — relatief vergelijkbaar; testaudio2: 0/19 segmenten
  onzeker op segmentniveau vs. 22/118 woorden onzeker — **op woordniveau
  duikt er dus onzekerheid op die op segmentniveau onzichtbaar was**, omdat
  korte woorden de coverage/margin-drempels van `DiarizationConfig`
  (getuned voor hele segmenten) makkelijker onderschrijden). Dat is een
  eerlijke prijs van meer granulariteit: meer zichtbare onzekerheid, niet
  meer fouten per se.

**Voorbeeld — crosstalk/noise bij zeer korte woorden (testaudio5, rand van
het fragment, rumoerig):**
```
45.26-45.54  Hoe          -> MAIN_SPEAKER   (zeker)
45.54-45.74  is           -> MAIN_SPEAKER   (zeker)
45.74-45.74  het          -> onzeker (nul-duur woord)
45.74-45.84  een          -> OTHER_SPEAKER_2 (zeker)
45.84-45.96  fackie...    -> OTHER_SPEAKER_2 (zeker)
```
Dit ÍS technisch een "zekere" split op woordniveau (`mixed_speakers_confident
= True`), maar de tekst zelf is ASR-garbled en de woorden zijn extreem kort
(100-200ms) — dit leest eerder als een crosstalk-artefact dan een
betrouwbare, leesbare sprekerwissel. **Niet elke "zekere" split is
inhoudelijk bruikbaar** — zie ook Stap 5/AUDIO5 hieronder.

## Stap 4 — helpt speaker recognition de diarization corrigeren?

Geëvalueerd op **twee granulariteiten**, met een cruciaal verschillend
resultaat (zie AUDIO2 hieronder voor waarom dit onderscheid het hele punt
van deze stap is):

- **turn_level**: Stap 3's `readable_turns` (grenzen = diarization-turns).
- **segment_level**: Stap 2's eigen ASR-segmenten (grenzen = VAD/ASR,
  **onafhankelijk** van diarization-turns) — dezelfde granulariteit als het
  eerdere `speaker_recognition/`-experiment gebruikte.

| Fragment | Niveau | Spraakstukken | Geëvalueerd (≥1.0s) | Consistent | Conflict: diar=DOCENT, sim laag | Conflict: diar=OTHER, sim hoog |
|---|---|---|---|---|---|---|
| testaudio1 | turn_level | 15 | 5 | 4 | 1 | 0 |
| testaudio1 | segment_level | 9 | 8 | 5 | 2 | 1 |
| testaudio2 | turn_level | 30 | 7 | 7 | **0** | 0 |
| testaudio2 | segment_level | 19 | 13 | 11 | **2** | 0 |
| testaudio5 | turn_level | 40 | 8 | 8 | 0 | 0 |
| testaudio5 | segment_level | 18 | 13 | 10 | 2 | 0 |

Drempel: cosine similarity ≥ 0.35 = DOCENT — zelfde waarde als
`speaker_recognition/comparison/results.md`, en zoals daar **uitdrukkelijk een
experimentele instelling, geen bewezen betrouwbaar criterium** (gekozen door
de similarity-verdeling op één steekproef te inspecteren, niet gevalideerd op
dit materiaal). Minimumduur om te embedden: 1.0s (zelfde reden als daar —
kortere stukken gaven daar onbetrouwbare scores).

Elk geëvalueerd spraakstuk in de output-JSON bewaart drie aparte velden naast
elkaar — `diarization_label` (het oorspronkelijke, ongewijzigde
diarization/assign_speakers-label), `similarity` (de recognition-score), en
`recognition_label` (het eventuele nieuwe label) — plus `agreement` en een
expliciete `conflict`-boolean die alleen aangeven OF de twee elkaar
tegenspreken, zonder ooit een winnaar te kiezen: `resolved_label` staat
altijd op `null`. Geen enkel bestaand label wordt stilzwijgend overschreven.

Runtime: modelload eenmalig ~6.0s voor alle fragmenten samen; één embedding
(zelfs van de 22.9s-referentieclip) kostte 0.56s — de recognition-stap voegt
in de praktijk enkele seconden toe, geen relevante factor in de totale
doorlooptijd.

## Stap 5 — gerichte evaluatie

### AUDIO 1 — "Dit ben jij. Dit ben ik."

Handmatige transcriptie: **Docent**: "Dus dit ben jij?" / **Leerling**:
"Dit ben ik." — twee sprekers, één whisper-segment (9.40-11.14s) in zowel de
baseline als dit experiment.

- **Baseline (A)**: geeft het hele segment één label (`MAIN_SPEAKER`, zie
  origineel `Data-local/processed/diarization/testaudio1_fragment_diarized.json`).
  Fout voor de helft van de tekst.
- **Word-level attribution (B, turn_level)**: **correct gesplitst** —
  "Dit ben jij." → `MAIN_SPEAKER` (coverage 1.0, 1.0), "Dit ben ik." →
  `OTHER_SPEAKER_1` (coverage 1.0, 1.0, 0.69), **geen van beide onzeker**.
  Er zit een duidelijke ~0.5s stilte tussen "jij." (eindigt 10.06s) en het
  tweede "Dit" (begint 10.56s) — precies waar de sprekerwissel hoort, en
  precies waar de pyannote-turn-grens ook lag. **Dit is het kernresultaat
  van dit experiment: hetzelfde soort correctie die de WhisperX-vergelijking
  liet zien, nu bereikt met alleen `word_timestamps=True` + de bestaande
  pyannote-turns, zonder aparte venv/dependencies.**
- **Recognition (C, segment_level)**: op de ongesplitste baseline-achtige
  segmentgrens (9.40-11.14s als één stuk) geeft de embedding een lage
  similarity (0.29, < 0.35 drempel) — voorspelt **OTHER** voor het hele
  blok. Dat is fout voor de "Dit ben jij"-helft, begrijpelijk (het gemiddelde
  van twee stemmen, met de leerling die het laatst spreekt en dus qua
  eindtoon domineert) maar laat zien dat recognition op een gemengd segment
  **niet zomaar** de plek van word-level attribution kan innemen — het geeft
  hooguit een vlag ("dit segment is verdacht"), geen correcte sub-splitsing.

**Conclusie AUDIO1**: de docent-leerlingwissel wordt door **B correct
herkend**; door A gemist; door C (op segmentniveau) fout ingeschat maar wel
terecht als "verdacht" gevlagd.

### AUDIO 2 — diarization kent bijna alles aan één spreker toe

Baseline + Stap 3 (turn_level) bevestigen exact wat de eerdere
WhisperX-vergelijking al vond: de pyannote-diarization zelf detecteert hier
nauwelijks een wissel (2 ruwe sprekers, 8 turns, en de segment-toewijzing
geeft alle 19 ASR-segmenten `MAIN_SPEAKER`). Woordniveau-koppeling (B) kan
dat niet herstellen: **0/19 segmenten gesplitst**, want zonder een
tweede turn is er niets om woorden aan te koppelen — elk woord in bv.
"Ruud heeft een brommer. De tekst gaat toch niet over brommer..." (een
4.24s-lange, docent+leerling-mengende readable_turn) overlapt met **dezelfde
ene turn**, dus krijgt **zeker, niet-onzeker** `MAIN_SPEAKER` — een
**foutief zelfverzekerd** label, niet een zichtbaar onzeker label.

Hier blijkt het belang van het turn_level/segment_level-onderscheid uit
Stap 4: op **segment_level** (Stap 2's eigen, kortere ASR-segmenten, los van
de diarization-turn-grenzen) vindt recognition wél twee duidelijke conflicten:

| Tijd | Tekst | Diarization-label | Similarity | Recognition-voorspelling |
|---|---|---|---|---|
| 6.84-8.32s | "Nee, maar het gaat ook niet om de brommer." | MAIN_SPEAKER | 0.117 | OTHER |
| 13.16-14.16s | "Met zijn vrouw." | MAIN_SPEAKER | 0.037 | OTHER |

Beide zijn, volgens de handmatige transcriptie, **leerling**-regels — de
recognition-stap identificeert ze correct als vermoedelijk niet de docent,
ondanks dat zowel de baseline als Stap 3's word-level attribution ze
(zeker, niet onzeker) als `MAIN_SPEAKER` bestempelen. Niet alle leerling-
regels worden gevangen (veel zijn <1s en dus niet geëvalueerd, bv. "Nee."
"Jawel." — zie Stap 4's minimumduur), maar het bewijst het punt: **recognition
op ASR-segmentniveau, losgekoppeld van de diarization-turns, ziet iets wat
noch de baseline noch woordniveau-koppeling ziet.**

**Conclusie AUDIO2**: woordniveau-koppeling (B) levert **geen** bruikbare
docent/leerling-info op zolang de onderliggende diarization niets vindt —
bevestigt de eerdere WhisperX-conclusie zonder WhisperX nodig te hebben.
Recognition **op segmentniveau** (C, niet gekoppeld aan diarization-turns)
levert wél een bruikbaar, zij het onvolledig, signaal.

### AUDIO 5 — meerdere sprekers, rumoer, overlap

- Word-level attribution vindt hier het minste "zeker gesplitste" segmenten
  (1/18) van de drie fragmenten, ondanks 5 ruwe sprekers/23 turns — de turns
  zijn kort en talrijk, maar vallen vaak niet middenin een ASR-segment.
- **Hoogste onzekerheidsgraad** van de drie fragmenten op woordniveau (18%
  onzeker, 13% overlap) — consistent met de beschrijving "rumoerig,
  overlappende spraak". 25 van de 40 readable turns zijn `speaker=None`
  (onzekere losse woorden) — meer dan de helft.
- Het ene "zeker gesplitste" segment (zie Stap 3's voorbeeld hierboven,
  "Hoe is het een fackie...") is zelf twijfelachtig: extreem korte woorden
  (100-200ms), ASR-garbled tekst, aan de rand van het fragment. **Een
  plausibel ogende "zekere" split is hier dus niet automatisch een
  betrouwbare split** — precies de waarschuwing die de opdracht vooraf gaf.
- Recognition op segmentniveau vindt ook hier 2 conflicten (diar=MAIN_SPEAKER,
  lage similarity) op regels die volgens de handmatige transcriptie
  leerling-regels zijn ("Jazeker. Dat zou wel invloed hebben." — dezelfde
  regel die in het eerdere `speaker_recognition`-experiment al als
  twijfelachtig was gemarkeerd). Voor de regel rond 40.88-42.80s ("Ik zeg
  het gewoon aan jou, want jij bent dan homo.") had het vorige experiment
  géén uitsluitsel ("onzeker" gelabeld bij gebrek aan match met de
  handmatige transcriptie) — de similarity-score hier (0.186, → OTHER) is
  nieuwe, bruikbare informatie die dat eerdere "onzeker" kan verfijnen,
  al blijft het zonder harde ground truth een aanwijzing, geen bewijs.

**Conclusie AUDIO5**: bevestigt de verwachting dat ruis/overlap de
betrouwbaarheid van zowel word-level attribution als recognition verlaagt —
niet doordat de technieken crashen of duidelijk fout gaan, maar doordat een
groot deel van het materiaal (korte, onzekere woorden; te korte
spraakstukken om te embedden) simpelweg buiten het bruikbare bereik valt.

## Stap 6 — vergelijking A / B / C

| | **A — bestaande pipeline** | **B — word-level attribution** (Stap 2+3) | **C — B + recognition refinement** (+ Stap 4, segment_level) |
|---|---|---|---|
| AUDIO1 docent/leerlingwissel | **Fout** (1 label voor 2 sprekers) | **Correct** (exacte split, geen onzekerheid) | Vlagt het baseline-segment terecht als verdacht, corrigeert het zelf niet |
| AUDIO2 (diarization ziet niets) | Alles MAIN_SPEAKER | **Geen verbetering** (0/19 gesplitst — kan de bron niet herstellen) | **2 conflicten gevonden** op segmentniveau — enige techniek die hier iets oplevert |
| Verkeerde speakerlabels | Onbekend zonder extra check | Kan ontstaan als *zeker* label wanneer diarization een grens mist (AUDIO2) — **gevaarlijker dan een gemiste split**, want niet zichtbaar als onzeker | Vangt een deel daarvan alsnog op (zie AUDIO2-tabel), maar alleen op spraakstukken ≥1.0s |
| Gemengde segmenten | Krijgen altijd 1 label (soms met `overlap=True`-vlag, geen split) | Kan splitsen **als** de diarization-turn-grens er is (AUDIO1); anders niet (AUDIO2) | Vlagt een gemengd segment als geheel als "verdacht" (lage/afwijkende similarity), splitst niet |
| Onzekerheid | Segment-niveau `uncertain_assignment`/`overlap`-vlaggen (bestaand) | Woord-niveau, explicieter en fijnmaziger (9-19% van woorden), maar **kan ook fout-zeker zijn** wanneer de turn-grens ontbreekt | `not_evaluated` voor te korte stukken (<1.0s) — een derde, aparte soort "we weten het niet" |
| Complexiteit | — | 1 extra ASR-pass (`word_timestamps=True`) + hergebruik van bestaande diarization/labeling-code; geen nieuwe modellen | + hergebruik van het bestaande WeSpeaker-model uit `speaker_recognition/`; geen nieuwe dependencies |
| Runtime (3 fragmenten samen) | ASR 147.3s + diarize 68.9s = 216.1s | ASR(word_ts) 115.8s + diarize 79.3s = **195.1s** (vergelijkbaar met A, **niet** de 2-3× overhead die WhisperX had) | + ~6s modelload + <1s per geëvalueerd spraakstuk — verwaarloosbaar |
| Nieuwe dependencies/omgeving | — | **geen** | **geen** |
| Codewijzigingen aan bestaande pipeline | — | **0 regels** | **0 regels** |

### Antwoord op de kernvraag

**Levert de extra component een aantoonbare verbetering op?** Ja, maar
**gescheiden per techniek en per situatie** — niet als één universele
upgrade:

- **B (word-level attribution) lost AUDIO1's probleem aantoonbaar op**,
  tegen verwaarloosbare extra kosten (geen nieuwe dependencies, vergelijkbare
  runtime als de baseline, 0 wijzigingen aan bestaande code) — en bereikt
  daarmee hetzelfde resultaat als de eerdere WhisperX-vergelijking liet zien,
  zonder een aparte Python 3.12-omgeving, ~100 extra dependencies, of de
  WhisperX-tekstencoding-kwestie.
- **B lost AUDIO2's probleem NIET op** — bevestigt (zonder WhisperX nodig te
  hebben) dat dit een fundamentele beperking van het diarizationmodel is,
  niet van de koppelmethode.
- **C (segment-level recognition) vindt wél bruikbare signalen in AUDIO2**,
  maar alleen als **losstaande vlag** (verdacht/niet verdacht), niet als
  correctie die automatisch een nieuw, betrouwbaar label teruggeeft — en
  alleen voor spraakstukken lang genoeg om te embedden (≥1.0s), wat een
  relevant deel van de korte leerling-regels uitsluit.
- **Een reëel, niet triviaal risico van B**: wanneer de diarization een
  wissel mist, geeft woordniveau-koppeling een **zeker-ogend** (niet
  `uncertain`) label dat toch fout kan zijn — dat is riskanter dan de
  baseline's eigen `overlap`/`uncertain_assignment`-vlaggen, die minstens
  aangeven "let hier op". Bij eventuele integratie zou dit expliciet
  ondervangen moeten worden (bv. door C's segment-level conflictsignaal
  altijd als extra check te draaien, niet alleen als B zelf onzeker is).

## Bekende beperkingen

- **Geen formele ground truth.** Zoals bij de eerdere experimenten: de
  "correct/fout"-uitspraken in Stap 5 zijn gebaseerd op handmatige
  tekstvergelijking met `Data-local/raw/testaudio{1,2,5}_manual.txt`, niet op
  tijdgeannoteerde labels. Voor AUDIO5 met name is een deel van de gevonden
  "conflicten"/"splits" plausibel maar niet hard geverifieerd.
- **Kleine steekproef**: 3 fragmenten van 30-46s. De 0.35-similarity-drempel
  en de 1.0s-minimumduur zijn ongewijzigd overgenomen uit het vorige
  experiment, niet opnieuw gevalideerd op dit (iets andere) materiaal.
- **`word_timestamps=True` verandert soms de segmentatie/tekst zelf**
  (zie Stap 2) — een reëel, nog niet volledig verklaard neveneffect dat
  verder onderzoek verdient vóór eventuele integratie in de hoofdpipeline.
- **De diarization is opnieuw gedraaid** (niet de oorspronkelijke run
  hergebruikt, want de ruwe turns werden nooit opgeslagen) — pyannote-
  diarization is niet volledig deterministisch; kleine run-to-run verschillen
  t.o.v. het origineel opgeslagen `*_diarized.json` zijn mogelijk (vandaar
  de aparte `baseline_segment_level_reference` in Stap 3's output, berekend
  met dezelfde verse turns, voor een eerlijke vergelijking).
- **De 0.5s-stilte in AUDIO1 die zo mooi samenviel met de turn-grens is één
  voorbeeld** — niet getest of dit ook werkt bij sprekerwissels zonder
  hoorbare pauze ertussen (bv. iemand die direct inspringt).
- Segment_level's `diarization_label`-matching (tijd-overlap tegen de baseline-
  segmenten) is zelf een heuristiek (≥50% overlap) — bij testaudio5's
  afwijkende segmentatie (18 vs. 21 baseline-segmenten) is dat niet voor elk
  segment een perfecte match.

## Voorlopige technische conclusie

`word_timestamps=True` + de bestaande pyannote-diarization-turns lossen het
"één ASR-segment, twee sprekers"-probleem net zo goed op als de eerdere
WhisperX-vergelijking liet zien (AUDIO1: exacte, niet-onzekere split), maar
dan **zonder nieuwe dependencies, zonder aparte Python-omgeving, en met
0 wijzigingen aan de bestaande pipeline** — dat maakt dit de goedkopere en
praktischer inzetbare route naar diezelfde verbetering. Het lost **niet** op
wanneer het onderliggende diarizationmodel zelf een sprekerwissel mist
(AUDIO2) — dat blijft, zoals eerder al vastgesteld, een beperking van het
diarizationmodel, niet van de koppelmethode. Daarvoor is een aparte,
diarization-onafhankelijke techniek nodig: speaker recognition op
ASR-segmentniveau (niet op de diarization-turns) vindt in dit experiment
wél een deel van de gemiste gevallen, zij het alleen als vlag, alleen voor
voldoende lange spraakstukken, en zonder de precisie van een echte
woordniveau-splitsing. Voor het prototype lijkt een combinatie het meest
kansrijk: woordniveau-attributie als primaire, precieze correctie waar de
diarization wél een grens vindt, aangevuld met segment-niveau recognition
als losstaande "twijfel-check" voor de gevallen waar dat niet zo is — beide
zijn met de bestaande stack en zonder nieuwe dependencies haalbaar.
