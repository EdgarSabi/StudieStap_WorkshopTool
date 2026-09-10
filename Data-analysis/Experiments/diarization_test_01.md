# Diarization test 01

Phase 2 — eerste kleine test van speaker diarization op een Nederlands
klasfragment. Doel: kunnen we betrouwbaar genoeg onderscheid maken tussen
**MAIN_SPEAKER** (docent / StudieStapper) en **OTHER_SPEAKER(S)** (leerlingen)?

Nog GEEN classificatie van didactische indicatoren in deze test.

---

## Opzet

| | |
|---|---|
| Audiobestand | `src/test-files/testaudio4_fragment.mp3` (120 s, offset 90–210 s uit `testaudio4.mp3`) |
| Duur | 120.0 s |
| Transcriptiemodel | faster-whisper `medium` — 87 segmenten, 144.8 s runtime (evt. later `large-v3` ter vergelijking) |
| Diarization backend | pyannote.audio 4.0.7 — pipeline `pyannote/speaker-diarization-3.1` |
| Device | CPU (torch 2.14.0+cpu) |
| Instellingen | `min_speakers` / `max_speakers`: **niet gezet** (pyannote koos zelf 2) · overige defaults uit `DiarizationConfig` (`overlap_min_ratio=0.15`, `uncertain_coverage_below=0.60`, `uncertain_margin_below=0.15`) |
| Runtime diarization | 74.0 s (≈ 0.6× realtime, exclusief model laden) |
| Runtime transcriptie (fragment) | 144.8 s |

> Audio-decoding: pyannote 4.x gebruikt standaard `torchcodec`, dat op Windows
> FFmpeg *shared* DLL's nodig heeft (niet aanwezig — alleen een statische
> `ffmpeg.exe`). `run_diarization.py` zet de mp3 daarom met de ffmpeg-CLI om naar
> 16 kHz mono wav, en `pyannote_backend.py` leest die wav zelf in (stdlib `wave`)
> en geeft pyannote een waveform-tensor. Zo wordt torchcodec omzeild.

Commando's (zie ook onderaan):

```
# 1. fragment knippen (90s..210s uit testaudio4.mp3, opnieuw geëncodeerd voor nette timestamps)
ffmpeg -y -ss 90 -t 120 -i src/test-files/testaudio4.mp3 -c:a libmp3lame -q:a 4 src/test-files/testaudio4_fragment.mp3

# 2. transcriptie van het fragment (Phase 1)
python run_transcription.py testaudio4_fragment.mp3 --dir test --model medium

# 3. diarization koppelen (Phase 2) -- pad is relatief vanuit Data-analysis/src
python run_diarization.py --transcript ../../Data-local/processed/testaudio4_fragment.json --dir test
```

---

## Sprekerinventaris (uit de run)

| Label | Raw id | Spreektijd | Aandeel |
|---|---|---|---|
| MAIN_SPEAKER | SPEAKER_00 | 81.7 s | 62.2 % |
| OTHER_SPEAKER_1 | SPEAKER_01 | 49.6 s | 37.8 % |

- Aantal ruwe sprekers: **2**
- Aantal turns: 63
- Segmenten totaal: 87 — 54 MAIN_SPEAKER, 33 OTHER_SPEAKER_1
- Segmenten met overlap-markering: **39 (45 %)**
- Segmenten met `uncertain_assignment`: **19 (22 %)**
- Segmenten zonder toegewezen spreker: 0
- "Schone" segmenten (geen overlap, niet onzeker): 31 MAIN, 12 OTHER
- Mediane `speaker_confidence`: MAIN 0.99 · OTHER 0.72
- Labelwissels tussen opeenvolgende segmenten: 33

**Aard van het fragment:** dit is geen klassikale scène maar een verhitte
één-op-één-confrontatie docent ↔ leerling ("Anita"), met "Emma" zijdelings
genoemd. Twee actieve stemmen is voor dít fragment dus aannemelijk — het zegt
nog niets over een fragment met meerdere gelijktijdig actieve leerlingen.

---

## Observaties

### Voorbeelden van correcte speaker-assignment
- `[2.4–5.1]  MAIN_SPEAKER  (c=0.99)` — "Nou, ik hoor jouw stem nou, toch?" (docent)
- `[31.5–34.3] OTHER_SPEAKER_1 (c=0.96)` — "Nou, dat mag u vinden, maar ik vind het ook heel gek dat jij dat heeft gezegd." (Anita)
- `[55.0–58.4] OTHER_SPEAKER_1 (c=1.0)` — "U gaat zonder reden, geeft u mij gewoon strafwerk. / Daar heb ik dus echt geen zin in." (Anita)
- `[71.2–75.8] MAIN_SPEAKER (c=1.0)` — "Emma, wat is het nou? / Zit je nou te krassen of…" (docent)
- `[86.4–89.3] MAIN_SPEAKER (c=0.96)` — "Weet je hoe vervelend het is dat je gewoon de les loopt te verstoren?" (docent)

De docent houdt over het hele fragment het label MAIN_SPEAKER, meestal met hoge
confidence. De langere, rustige leerlingbeurten gaan betrouwbaar naar
OTHER_SPEAKER_1.

### Voorbeelden van fouten
- `[98.5–99.2] MAIN_SPEAKER (c=0.51, OVL+UNC)` — "Meneer." → is vrijwel zeker de
  leerling die de docent aanspreekt; toegewezen aan MAIN. Wél gemarkeerd als onzeker.
- `[16.7–17.4] MAIN_SPEAKER (c=0.5, OVL+UNC)` — "Hou op!" → spreker ambigu, waarschijnlijk leerling.
- `[99.2–102.8]` snelle reeks "Nee, Anita." / "Ga gewoon weg." / "Ja, ga gewoon weg." / "Ga weg."
  → allemaal MAIN tijdens door-elkaar-schreeuwen; een deel hiervan is vermoedelijk
  de leerling. Grotendeels `uncertain_assignment=True`.
- `[50.4–51.6] MAIN_SPEAKER (c=1.0) maar UNC` — "Anita." Eén spreker, hoge
  confidence, tóch onzeker-gemarkeerd omdat de diarization-turn < 60 % van het
  ASR-segment dekt. → drempel-artefact, zie hieronder.

**Geen** opsplitsing van de docent over meerdere ids (er zijn maar 2 ids totaal).

### Overlap
45 % van de segmenten krijgt de overlap-vlag. Een groot deel daarvan zijn korte
backchannels ("Ja.", "Nee.", "Zeker.", "Ja?") op turn-grenzen, waar de drempel
`overlap_min_ratio=0.15` al aanslaat. Echte, zware crosstalk zit vooral in het
stuk ± 95–120 s (ruzie-achtig door elkaar praten); daar valt de confidence naar
≈ 0.5 en staan overlap + uncertain samen aan. De vlaggen doen dus hun werk als
*"hier voorzichtig zijn"*-signaal, maar het absolute aantal is te hoog om als
kwantitatieve overlap-maat te gebruiken zonder de drempel bij te stellen.

### Gemiste leerlinguitspraak (ASR miste tekst)
Alle 87 ASR-segmenten kregen een spreker (0 unassigned). **Belangrijke beperking:**
`run_diarization.py` koppelt transcript-segmenten → sprekers, niet andersom.
Spraak die pyannote wél detecteert maar die Whisper niet transcribeert
(zachte/overschreeuwde leerlingreacties) komt in deze output *niet* voor. De
afwezigheid van een leerlingsegment is dus geen bewijs dat er geen leerling
sprak — het huidige script maakt zulke gemiste spraak alleen niet zichtbaar
(er wordt niet gerapporteerd op diarization-turns zonder bijbehorend segment).

---

## Beoordeling (de 8 vragen)

| Vraag | Antwoord |
|---|---|
| Houdt dezelfde hoofdspreker meestal hetzelfde label? | Ja. De docent = MAIN_SPEAKER over het hele fragment, mediane confidence 0.99. |
| Worden leerlingreacties als andere spreker(s) herkend? | Ja, voor de duidelijke beurten betrouwbaar (OTHER_SPEAKER_1). Korte kreten tijdens crosstalk gaan soms mis. |
| Wordt de hoofdspreker niet onnodig over veel ids opgesplitst? | Nee, geen opsplitsing — 2 ids totaal, docent consequent één id. |
| Wat gebeurt er bij overlap? | pyannote kiest de dominante stem in het venster; onze `overlap`- en `uncertain_assignment`-vlaggen slaan aan (c ≈ 0.5). 45 % overlap-vlaggen = drempel staat gevoelig. |
| Wat gebeurt er als ASR een leerlinguitspraak mist? | Dan ontbreekt dat segment volledig; de huidige koppeling (segment → spreker) maakt gemiste spraak niet zichtbaar. Mag niet als "geen leerling" gelezen worden. |
| Hoe lang duurt diarization (CPU)? | 74 s voor 120 s audio (≈ 0.6× realtime), plus eenmalig model laden. Een les van 45 min ≈ 28 min diarization op deze CPU. |
| Is MAIN_SPEAKER vs OTHER_SPEAKER(S) technisch haalbaar hier? | Voor dit 2-stemmige fragment: ja, goed genoeg voor het MVP-doel (docentbeurten schoon isoleren). Nog niet getest met 3+ gelijktijdig actieve leerlingen. |
| Verschil medium- vs large-v3-transcript (indien getest)? | Getest — zie "Vervolgtest 02" hieronder. Kort: speakerlabels blijven vrijwel gelijk (96.8 % identiek); large-v3 geeft betere tekst, strakkere segmentgrenzen en hogere assignment-confidence (minder `uncertain`). |

---

## Vervolgtest 02 — effect van betere ASR op de speaker-gelabelde output

**Opzet:** exact hetzelfde 120 s-fragment, één diarization-run (63 turns, zelfde
label-map, 72 s), gekoppeld aan twee transcripties:

| | `medium` | `large-v3` |
|---|---|---|
| ASR-runtime (120 s audio, CPU) | 144.8 s | 243.8 s (≈ 1.7× medium, ≈ 2.0× realtime) |
| Segmenten | 87 | 95 |
| per label | 54 MAIN / 33 OTHER | 59 MAIN / 36 OTHER |
| toegewezen spreektijd (som segmentduur) | 77.0 s MAIN / 40.0 s OTHER | 62.0 s MAIN / 32.8 s OTHER |
| overlap-vlaggen | 39 | 40 |
| uncertain-vlaggen | **19** | **16** |
| unassigned | 0 | 0 |
| mediane `speaker_confidence` | MAIN 0.99 · OTHER **0.72** | MAIN 1.00 · OTHER **0.92** |

**Tijd-raster (0,25 s) vergelijking van het toegekende spreker-label:**
- 79 % van de tijdlijn wordt door béíde transcripties met een segment gedekt;
- daarvan **96,8 % identiek speaker-label**, 3,2 % verschil;
- de verschillen zijn bijna allemaal losse 0,25 s-cellen op segmentgrenzen
  (grens-jitter), niet echte hertoewijzingen. Slechts één verschilblok is ≥ 1 s
  (`[116.75–117.75]`).
- "alleen medium heeft spraak": 22,5 s — dit is vooral medium die grenzen oprekt
  en korte filler-segmentjes ("Ja, doei.", "Nee.", "Zeker.") toevoegt, niet
  medium die méér echte leerlingspraak vangt. "Alleen large-v3": 0,2 s.

### Veranderen de speaker-assignments?
Nauwelijks. De diarization doet het sprekerwerk; ASR-kwaliteit verschuift *wie*
een segment krijgt vrijwel niet (96,8 % gelijk).

### Worden meer of minder leerlinguitingen zichtbaar?
Marginaal meer segmenten met large-v3 (+3 OTHER), maar de totale toegewezen
OTHER-spreektijd daalt (strakkere grenzen). Door ASR gemiste leerlingspraak
blijft in béíde gevallen onzichtbaar — dat is een beperking van de koppeling
(segment → spreker), niet van het ASR-model.

### Veranderen overlap/uncertain?
Overlap ≈ gelijk (39 → 40; echte crosstalk blijft). `uncertain` daalt (19 → 16)
en de confidence stijgt duidelijk (mediaan OTHER 0.72 → 0.92): strakkere
large-v3-grenzen vallen vaker volledig binnen één diarization-turn.

### Stukken waar large-v3 betere tekst geeft, zelfde speaker blijft goed
- `[110–112]` "…doet me echt geen ene zak" → "…**boeit** me echt geen ene zak" — beide OTHER.
- `[112–114]` medium "Het gaat niet gewoon met de periode schrijven." (wartaal)
  → large-v3 "**We gaan niet van het papier overschrijven.**" (leerling weigert
  overschrijven) — beide OTHER.
- `[19–21]` "openschrijven" → "**overschrijven**" — beide MAIN.

### Stukken waar betere ASR de speaker-koppeling verbetert
- `[50.4–51.6]` "Anita." — medium: MAIN `c=1.0` maar tóch `uncertain` (segment te
  breed, lage turn-dekking). large-v3: `[50.5–50.8]` "Anita." MAIN `c=1.0`,
  **geen `uncertain`** — strakkere grens valt binnen de turn.
- `[58–66]` docentbeurt: medium hakt dit in 7 korte stukjes met 2× `uncertain`
  en lage confidence; large-v3 maakt er 2 samenhangende MAIN-segmenten van
  (minder `uncertain`).

### Runtimeverschil
medium 144.8 s vs large-v3 243.8 s voor 120 s audio (+ vast ~72 s diarization,
onafhankelijk van het ASR-model). Voor een les van 45 min: ruwe schatting
medium ≈ 55 min, large-v3 ≈ 90 min aan ASR op deze CPU, plus ~27 min diarization.

Gekoppelde outputs: `Data-local/processed/diarization/testaudio4_fragment_medium_diarized.json`
en `…_large-v3_diarized.json`.

---

## Voorlopige conclusie

Voor een lastig, luidruchtig maar in de kern twee-stemmig klasfragment werkt de
combinatie faster-whisper `medium` + pyannote 3.1 goed genoeg voor het MVP-doel:
de docent wordt consequent en met hoge zekerheid als MAIN_SPEAKER herkend, en de
leerling als OTHER_SPEAKER_1. Fouten concentreren zich in door-elkaar-heen
schreeuwen en worden daar grotendeels met `overlap` / `uncertain_assignment`
gemarkeerd, dus bruikbaar mét die onzekerheidssignalen erbij.

Kanttekeningen: (1) alleen op één 2-sprekerfragment getest; (2) de overlap-drempel
is te gevoelig voor kwantitatief gebruik; (3) de `uncertain`-vlag slaat soms aan
bij een op zich zekere toewijzing (lage segmentdekking); (4) door ASR gemiste
leerlingspraak is in de output onzichtbaar; (5) `MAIN_SPEAKER = meeste spreektijd`
klopt zolang de docent domineert — bij een fragment waarin een leerling langer
aan het woord is dan de docent kan het omdraaien.

**Beslissing:** **geschikt (met voorbehoud)** voor vervolg — pyannote 3.1 blijft
de eerste kandidaat-backend; herbeoordelen op een fragment met meerdere actieve
leerlingen en tijdens de classificatiefase.

---

## Afsluiting Phase 2 — de drie sluitvragen

**Is `medium` voorlopig voldoende voor verdere ontwikkeling?**
Ja. De speaker-gelabelde structuur is met `medium` identiek aan die met `large-v3`
(96,8 % gelijk op tijdrasterniveau); de tekst is bruikbaar voor ontwikkelwerk en
`medium` is ~1,7× sneller. Voor het bouwen en itereren van de volgende fase is
`medium` het praktische werkpaard.

**Blijft `large-v3` nuttig als kwaliteitsreferentie?**
Ja. `large-v3` levert merkbaar betere tekst op de rommelige stukken, strakkere
segmentgrenzen, hogere assignment-confidence en minder `uncertain`-vlaggen. Het
is de juiste keuze voor de definitieve / handmatig gecontroleerde runs en als
ijkpunt om `medium`-output tegen af te zetten.

**Is de huidige speaker-koppeling goed genoeg om door te gaan naar de volgende fase?**
Ja, voor het MVP-doel (leerlingtekst als context bij de analyse van het
docenthandelen). De docent wordt betrouwbaar als MAIN_SPEAKER geïsoleerd, en de
onzekere plekken (overlap, door elkaar praten) zijn gemarkeerd in plaats van
stilzwijgend fout. De volgende fase moet die `overlap` / `uncertain_assignment`
/ `speaker_confidence`-signalen wél respecteren.

**Openstaande punten (meenemen, geen blocker):**
1. Alleen getest op 2-stemmige fragmenten — nog niet met 3+ gelijktijdig actieve leerlingen.
2. `overlap_min_ratio=0.15` is te gevoelig voor kwantitatief gebruik; ijken tegen handmatige observatie.
3. `uncertain` slaat soms aan bij een op zich zekere toewijzing (lage turn-dekking van een breed segment) — drempellogica kan verfijnd.
4. Door ASR gemiste leerlingspraak is onzichtbaar; overweeg diarization-turns zónder transcript-segment te rapporteren.
5. `MAIN_SPEAKER = meeste spreektijd` kan omdraaien als een leerling langer spreekt dan de docent in een fragment.
6. **Mogelijke toekomstige verbetering (niet nu bouwen):** speaker enrollment /
   voiceprint van de vaste StudieStapper, zodat MAIN_SPEAKER op stemidentiteit
   wordt bepaald i.p.v. op spreektijd, en labels consistent blijven over
   meerdere opnames. Buiten scope van de MVP; hier alleen genoteerd.
