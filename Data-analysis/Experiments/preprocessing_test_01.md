# Preprocessing test 01

Phase 3 — eerste test van het samenvoegen van diarized ASR-segmenten tot
logische speaker turns, met behoud van traceability en expliciete
context-(on)zekerheid. Nog GEEN didactische classificatie (geen regels voor
vraaggedrag, begripscontrole, gerichte feedback of uitleg-vs-interactie).

---

## Gebruikte input

Het bestaande Phase 2-fragment, hergebruikt zonder wijziging:

| | |
|---|---|
| Bron 1 | `Data-local/processed/diarization/testaudio4_fragment_medium_diarized.json` (87 segmenten, faster-whisper `medium`) |
| Bron 2 (extra check) | `Data-local/processed/diarization/testaudio4_fragment_large-v3_diarized.json` (95 segmenten, `large-v3`) |
| Audio | `src/test-files/testaudio4_fragment.mp3` (120 s, docent-leerling-confrontatie) |
| Diarization | ongewijzigd overgenomen uit Phase 2 (pyannote 3.1, 2 sprekers: MAIN_SPEAKER / OTHER_SPEAKER_1) |

Commando:
```
python run_preprocessing.py --diarized ../../Data-local/processed/diarization/testaudio4_fragment_medium_diarized.json
```

## Preprocessing-stappen

> Deze sectie beschrijft de **huidige** (conservatieve) merge-regel, zoals
> vastgesteld in de "Update — conservatievere merge-regel" sectie verderop.
> De oorspronkelijke, mildere regel die daaraan voorafging staat daar ook nog
> als historisch record.

1. **`build_speaker_turns`** — een segment is **geïsoleerd** (altijd een eigen
   singleton turn, nooit samengevoegd met een buursegment) zodra het
   `speaker=None` is, `uncertain_assignment=True`, of `overlap=True`. Alleen
   twee opeenvolgende, **schone** (`overlap=False` én `uncertain_assignment=False`)
   segmenten van dezelfde spreker worden samengevoegd tot één turn, en dan nog
   alleen als het gat ertussen ≤ `max_gap_within_turn_seconds`
   (heuristische default: **1,5 s**). Gevolg: een turn met meer dan 1
   samengevoegd segment is per constructie altijd `overlap=False` en
   `uncertain_assignment=False` — onzekere/overlappende tekst wordt dus nooit
   inhoudelijk vermengd met zekere tekst, maar blijft als losse, volledig
   inspecteerbare turn bestaan.
2. **`attach_context`** — bepaalt per turn, tov. de buurturns: `gap_before/after_seconds`,
   `context_available_before/after` (is er ǘberhaupt een buurturn) en, los
   daarvan, `context_uncertain_before/after` (is die buurturn zelf `overlap`/
   `uncertain_assignment`, of ligt hij verder weg dan `large_context_gap_seconds`,
   heuristische default: **3,0 s**). Een ontbrekende buurturn ⇒ `context_available=False`
   maar **niet automatisch** `context_uncertain=True`.
3. **`turn_stats`** — puur beschrijvende hulpfuncties: `duration_by_speaker`
   (werkelijke spreektijd — som van de duraties van de originele
   `source_segments` per spreker, ONafhankelijk van hoe segmenten toevallig
   zijn samengevoegd), `turn_span_by_speaker`/`turn_span` (`turn.end - turn.start`,
   inclusief eventuele gaten binnen een turn — nadrukkelijk iets anders dan
   spreektijd) en `count_speaker_switches`. Geen classificatie.

Output: `models.processed.ProcessedTranscript`, apart van het Phase 1/2-schema;
de bron-JSON wordt alleen gelezen, nooit aangepast.

## Traceability-check

- `sum(turn.n_segments_merged for turn in turns) == original_segment_count`
  klopt exact voor beide bronnen (medium: 87 = 87, large-v3: 95 = 95) — geen
  segment verdwijnt of wordt dubbel geteld.
- Elke turn bevat `source_indices` (positie in de originele segmentlijst) én
  `source_segments`: de volledige originele `TranscriptSegment`-objecten,
  inclusief `speaker_raw`, `avg_logprob`/`no_speech_prob`/`compression_ratio`,
  `quality_flags` — niets is samengevat of weggelaten.
- `turn.start`/`turn.end` zijn letterlijk het begin van het eerste en het einde
  van het laatste bron-segment — nooit herberekend.

## Voorbeeld vóór preprocessing (5 originele segmenten, medium)

```
[2.44-5.08]  MAIN_SPEAKER  "Nou, ik hoor jouw stem nou, toch?"
[5.08-5.76]  MAIN_SPEAKER  "Ja, dat klopt."
[5.76-6.44]  MAIN_SPEAKER  "Ja, nou."
[6.44-7.56]  MAIN_SPEAKER  "Omdat ik protesteer."
[7.56-9.2]   MAIN_SPEAKER  "Ja, precies. Jij protesteert."
```
(alle vijf schoon: `overlap=False`, `uncertain_assignment=False` — daarom komen ze in aanmerking om samengevoegd te worden onder de huidige, conservatieve merge-regel.)

## Voorbeeld na preprocessing (dezelfde 5 segmenten → 1 turn)

```json
{
  "turn_id": 2,
  "speaker": "MAIN_SPEAKER",
  "start": 2.44,
  "end": 9.2,
  "text": "Nou, ik hoor jouw stem nou, toch? Ja, dat klopt. Ja, nou. Omdat ik protesteer. Ja, precies. Jij protesteert.",
  "n_segments_merged": 5,
  "source_indices": [2, 3, 4, 5, 6],
  "overlap": false,
  "uncertain_assignment": false,
  "context_available_before": true,
  "context_available_after": true,
  "context_uncertain_before": true,
  "context_uncertain_after": true
}
```
(`context_uncertain_before=true` hier omdat de voorgaande turn — "Dat vind ik
echt niet eerlijk." — zelf `overlap=True` draagt; dat maakt turn 2 zelf niet
onzeker, maar zegt wel dat de context ervóór voorzichtig gelezen moet worden.)
(`source_segments` bevat de 5 volledige originele objecten; hier ingekort weergegeven.)

Ter vergelijking: turn 0 (het allereerste segment) toont het "geen context"-geval:
`context_available_before: false, context_uncertain_before: false` — géén
voorganger, en dat wordt dus expliciet NIET als onzeker gelabeld (vereiste #2).

## Resultaten — oorspronkelijke merge-regel (zie "Update" hieronder voor de aangepaste regel)

> Deze sectie beschrijft de eerste versie van de merge-regel (speaker + gap,
> onzekerheid blokkeert niet). Ze is hieronder vervangen door een
> conservatievere regel; ik laat dit stuk staan als historisch record i.p.v.
> het stilzwijgend te overschrijven.

| | medium (bron) | large-v3 (extra check) |
|---|---|---|
| Segmenten → turns | 87 → **34** | 95 → **33** |
| Single-segment turns / samengevoegd | 13 / 21 (max 12 samengevoegd) | 10 / 23 (max 12 samengevoegd) |
| Spreker-wissels tussen turns | 33 | 31 |
| Spreektijd per label ⚠️ | MAIN 78.2 s / OTHER 40.0 s | MAIN 75.7 s / OTHER 34.7 s |
| Turns met `overlap` | 22 | 20 |
| Turns met `uncertain_assignment` | 14 | 12 |
| Turns zonder buurturn (`context_available=False`) | 1 vóór / 1 na (start & einde fragment) | 1 / 1 |
| Turns met onzekere buurturn (`context_uncertain=True`) | 24 vóór / 25 na | 20 / 21 |

⚠️ Deze "Spreektijd per label"-rij werd berekend als `turn.end - turn.start`
(turn-span), niet als som van bronsegment-duraties — dat bleek een fout, zie
de "Correctie: spreektijd los van de merge-regel" sectie verderop. Cijfers
hier ongewijzigd als historisch record; gebruik de gecorrigeerde waarden
verderop in het rapport.

De large-v3-run bevestigt dat de preprocessing-stap generaliseert (geen crash,
vergelijkbare turn-structuur); geen volledige medium-vs-large-v3-vergelijking
hier — die is al in `diarization_test_01.md` gedaan.

## Gevallen waar samenvoegen goed werkt (oorspronkelijke regel)

- **Turn 2** `[2.4–9.2]` (hierboven): 5 korte, rustige MAIN-segmenten zonder
  overlap/onzekerheid worden één samenhangende docent-uitspraak.
- **Turn 28** `[91.1–105.2]`, 12 segmenten samengevoegd tot één 14 s
  MAIN-monoloog ("Ja, maar ik vind het niet fijn... Anita. Meneer. Nee, Anita.
  Ga gewoon weg. ..."). Ook al zitten hier onzekere/overlap-segmenten tussen
  (bv. "Meneer." — vermoedelijk de leerling, zie `diarization_test_01.md`), de
  turn blijft correct `overlap=True, uncertain_assignment=True` — zichtbaar
  onzeker, niet stilzwijgend weggepoetst. Dit is precies zo'n lange
  docent-monoloog die later relevant is voor "uitleg vs interactie" (nu nog
  niet geclassificeerd).
- **Docent-leerling-docent-patroon blijft intact**: de eerste 5 turns lopen
  MAIN → OTHER → MAIN → OTHER → MAIN, exact volgens het originele
  transcript. Over het hele fragment volgt vrijwel elke turn een
  sprekerwissel (33 wissels op 34 turns) — het fragment is één lang
  wisselgesprek, en dat patroon overleeft het samenvoegen.

## Gevallen waar context onzeker blijft

> Turn-nummers hieronder zijn bijgewerkt naar de huidige (aangepaste)
> merge-regel — met de oorspronkelijke regel lagen dezelfde momenten op
> andere turn-id's (zie "Update" verderop).

- **Randen van het fragment**: turn 0 (start) heeft geen `context_available_before`,
  turn 69 (einde, met de huidige regel 70 turns totaal) geen
  `context_available_after` — terecht "geen context", niet "onzekere context"
  (vereiste #2 hierboven).
- **Rond de ruzie-episode (± 95–120 s)**: bijna elke turn heeft
  `context_uncertain_before/after = true`, omdat de buurturns zelf `overlap`
  of `uncertain_assignment` dragen (kort door elkaar heen praten, zie
  `diarization_test_01.md`). Voor een latere "gerichte feedback"-classifier
  betekent dit concreet: een docent-turn in dit stuk zou pas beoordeeld mogen
  worden als ook `context_uncertain_before=False` — hier dus meestal niet het
  geval, en dat is zichtbaar zonder dat er iets is weggegooid.
- **Turn 33 → 34**: een echte stilte van 1,52 s (`gap_after_seconds=1.52`,
  onder de 3,0 s-drempel dus niet als "groot gat" geteld) tussen "Ja, doei."
  (MAIN, `overlap=True`) en "Doei." (OTHER) — een grensgeval waar de drempel
  de uitkomst bepaalt; met een lagere drempel zou dit wél als groot gat gelden.
- **Turn 34 → 35** laat de striktere merge-regel in actie zien: "Doei."
  (OTHER, schoon) en "Hou je bek." (OTHER, `uncertain_assignment=True`) liggen
  direct na elkaar (`gap=0.0 s`, zelfde spreker) maar worden tóch niet
  samengevoegd — want "Hou je bek." is zelf onzeker en is daarom altijd een
  eigen singleton turn, ook al zou de oude regel (gap + spreker) ze wel hebben
  samengevoegd.

## Update — conservatievere merge-regel

**Aanleiding:** in de lange turn `[91.1–105.2]` hierboven zat "Meneer." —
vermoedelijk de leerling die de docent aanspreekt (zie `diarization_test_01.md`)
— inhoudelijk samengevoegd met de zekere docenttekst eromheen. De
`overlap`/`uncertain_assignment`-vlaggen op turn-niveau maakten dat wel
zichtbaar, maar de tekst zelf las al als één MAIN_SPEAKER-uitspraak. Dat is
ongewenst zodra iemand later naar de *tekst* van een turn kijkt.

**Aangepaste regel** (`preprocessing/turns.py`): een segment met
`speaker=None`, `uncertain_assignment=True` óf `overlap=True` is **altijd**
een losstaande singleton-turn — het wordt nooit samengevoegd met een
buursegment, in geen van beide richtingen. Alleen twee opeenvolgende, schone
(`overlap=False` én `uncertain_assignment=False`) segmenten van dezelfde
spreker binnen `max_gap_within_turn_seconds` vormen samen één normale turn.
Gevolg: een turn met `n_segments_merged > 1` heeft per constructie altijd
`overlap=False` en `uncertain_assignment=False`. Niets wordt weggegooid — elk
onzeker/overlappend segment blijft een eigen, volledig inspecteerbare turn.

**Documentatie-aanpassing** (`models/processed.py`): expliciete opmerking
toegevoegd dat een latere classifier **twee** dingen moet checken voordat een
turn beoordeeld wordt — niet alleen de context (`context_available_*` /
`context_uncertain_*`), maar ook of de turn zelf schoon is
(`overlap=False` en `uncertain_assignment=False`). Een schone turn met een
onzekere buur, én een onzekere turn met een schone buur, zijn allebei
gevallen waarin een classifier zou moeten terughoudend zijn.

### Episode 91–105 s: vóór en ná

**Vóór** (oorspronkelijke regel) — 1 turn, 12 segmenten:
```
T28 [91.1-105.2] MAIN_SPEAKER  n=12  OVL,UNC
    "Ja, maar ik vind het niet fijn... Anita. Meneer. Nee, Anita.
     Ga gewoon weg. Ja, ga gewoon weg. Ga weg. Ja, nou ik sta er.
     Nou, hoe vind je dat?"
```
"Meneer." leest hier als onderdeel van dezelfde docentuitspraak.

**Ná** (aangepaste regel) — 7 turns:
```
T48 [ 91.1- 98.5] MAIN_SPEAKER  n=5           "Ja, maar ik vind het niet fijn als je in die
                                                honders schrift zit te krassen. ... Ja?"
T49 [ 98.5- 99.2] MAIN_SPEAKER  n=1  OVL,UNC   "Meneer."
T50 [ 99.2- 99.8] MAIN_SPEAKER  n=1  OVL,UNC   "Nee, Anita."
T51 [ 99.8-100.6] MAIN_SPEAKER  n=1  OVL,UNC   "Ga gewoon weg."
T52 [100.6-101.9] MAIN_SPEAKER  n=1  OVL,UNC   "Ja, ga gewoon weg."
T53 [101.9-102.8] MAIN_SPEAKER  n=1  OVL       "Ga weg."
T54 [102.8-105.2] MAIN_SPEAKER  n=2            "Ja, nou ik sta er. Nou, hoe vind je dat?"
```
De twee schone docentstukken (T48, T54) staan nu los van de vijf
onzekere/overlappende eenregelige fragmenten ertussen — inclusief "Meneer.",
dat nu een eigen, duidelijk gemarkeerde turn is in plaats van opgelost in de
docenttekst. Merk op dat álle vijf tussenliggende turns hetzelfde
`speaker=MAIN_SPEAKER`-label houden als vóór de wijziging — de diarization-
toewijzing verandert niet, alleen het wel/niet samenvoegen.

### Resultaten — aangepaste regel (heel fragment)

| | medium | large-v3 |
|---|---|---|
| Segmenten → turns | 87 → **70** (was 34) | 95 → **72** (was 33) |
| Turns met `overlap` | 39 (was 22) | 40 (was 20) |
| Turns met `uncertain_assignment` | 19 (was 14) | 16 (was 12) |
| Turns zonder buurturn | 1 / 1 | 1 / 1 |
| Turns met onzekere buurturn | 43 vóór / 44 na (was 24/25) | 40 / 41 (was 20/21) |
| **Spreektijd** per label (`duration_by_speaker`, som segment-duraties) | MAIN 77.0 s / OTHER 40.0 s | MAIN **61.96** s / OTHER 32.78 s |
| `turn_span` per label (`turn_span_by_speaker`, incl. gaps binnen een turn) | MAIN 77.0 s / OTHER 40.0 s | MAIN **68.0** s / OTHER 33.3 s |

Turns met `overlap`/`uncertain_assignment` stijgen nu naar exact het aantal
overlap/uncertain **segmenten** uit Phase 2 (39 resp. 19 voor medium) — logisch,
want zulke segmenten worden nooit meer samengevoegd tot één turn, dus turn-
telling = segment-telling voor die twee categorieën. Het aantal turns bijna
verdubbelt (34→70), wat te verwachten is: dit fragment is een verhitte
woordenwisseling met veel korte, onzekere/overlappende regels.

### Correctie: spreektijd los van de merge-regel

`turn_stats.duration_by_speaker` rekende spreektijd eerst als
`turn.end - turn.start`, opgeteld over turns. Dat is fout: die span omvat ook
eventuele kleine stiltes *binnen* een samengevoegde turn (het gat tussen twee
brondsegmenten), en zou dus — afhankelijk van hoe segmenten toevallig worden
samengevoegd — een andere spreektijd opleveren dan wanneer diezelfde
segmenten niet worden samengevoegd. Spreektijd hoort niet van de merge-regel
af te hangen.

**Fix:** `duration_by_speaker` telt nu de duur van elk oorspronkelijk
`source_segments`-item bij elkaar op, niet de turn-span. Omdat elk bron-
segment in precies één turn terechtkomt (traceability-invariant), is deze
som per spreker exact gelijk aan de werkelijke totale spreektijd in het
originele transcript, ongeacht hoe segmenten worden samengevoegd. De oude
`turn.end - turn.start`-berekening blijft apart bestaan als `turn_span`
(functie `turn_span_by_speaker` / `turn_span(turn)`) — nuttig als iemand
later wil weten hoeveel van de tijdlijn een turn *beslaat*, maar dat is
uitdrukkelijk iets anders dan spreektijd.

Op dit fragment maakt dat voor `medium` toevallig niets uit (77.04 s beide
kanten — geen van de samengevoegde turns bevat een gat tussen bronsegmenten),
maar voor `large-v3` wél: spreektijd MAIN = **61.96 s**, tegenover een
`turn_span` van 68.0 s — een verschil van ruim 6 s aan stiltes die eerst ten
onrechte als spreektijd meetelden. Dit bevestigt dat de twee metrics
daadwerkelijk verschillende dingen meten en dat de fix nodig was.

---

## Voorlopige conclusie — de 5 inspectiepunten

| Vraag | Antwoord |
|---|---|
| 1. Hoe zijn ASR-segmenten samengevoegd tot turns? | Zichtbaar en natrekbaar per turn via `source_indices`/`source_segments`; met de aangepaste regel 87→**70** (medium) resp. 95→**72** (large-v3) — alleen schone, opeenvolgende segmenten van dezelfde spreker smelten samen. |
| 2. Blijven docent-leerling-docent-interacties intact? | Ja — het MAIN↔OTHER-wisselpatroon is exact bewaard (33 resp. 31 sprekerwissels, ongewijzigd tov. de oorspronkelijke regel — alleen het wel/niet samenvoegen ván segmenten mét hetzelfde label verandert, niet de labels zelf). |
| 3. Blijft overlap/onzekerheid behouden? | Ja, en sterker dan voorheen: een onzeker/overlappend segment wordt nu nooit meer inhoudelijk vermengd met zekere buurtekst — het blijft altijd een eigen, volledig zichtbare turn. Een turn met meerdere samengevoegde segmenten is daardoor per constructie altijd schoon (`overlap=False`, `uncertain_assignment=False`). |
| 4. Zijn timestamps terug te leiden naar het origineel? | Ja — ongewijzigd; `turn.start/end` zijn de originele start/eind van het eerste/laatste bron-segment, traceability-invariant klopt exact voor beide regels. |
| 5. Geschikt als input voor latere classificatie? | Ja, en explicieter dan voorheen: een classifier moet **twee** dingen checken vóór het beoordelen van een turn — (a) is de turn zelf schoon (`overlap=False`, `uncertain_assignment=False`), en (b) is de relevante context beschikbaar én niet onzeker (`context_available_*` en `not context_uncertain_*`). Dit staat nu ook expliciet in `models/processed.py`. |

**Beslissing:** geschikt om mee door te gaan, met de aangepaste (conservatievere)
merge-regel als uitgangspunt. `max_gap_within_turn_seconds` (1,5 s) en
`large_context_gap_seconds` (3,0 s) blijven expliciet heuristische, voorlopige
keuzes (zie `config.PreprocessingConfig`) — nog niet gevalideerd tegen
handmatige beoordeling en verwacht te worden bijgesteld.

**Nog niet gedaan (bewust buiten scope):**
- geen didactische classificatie (vraaggedrag / begripscontrole / gerichte
  feedback / uitleg-vs-interactie) — die definities komen uit het onderzoek
  en worden apart gevalideerd;
- geen test op een fragment met `speaker=None`-segmenten (dit fragment had er
  0), dus die tak van de isolatie-regel is nog niet in de praktijk gezien;
- drempelwaarden nog niet gekalibreerd tegen meerdere/gevarieerde fragmenten;
- nog geen check of het bijna verdubbelde aantal (kortere) turns problemen
  geeft voor een latere classifier — dat is iets om in de gaten te houden
  zodra die er is.

**Vervolgacties:**
- Drempels (`max_gap_within_turn_seconds`, `large_context_gap_seconds`) ijken
  zodra er meer/gevarieerde fragmenten doorheen zijn gehaald.
- Testen op een fragment met minstens één `speaker=None`-segment.
- Zodra de didactische definities uit het onderzoek gevalideerd zijn: een
  classifier bouwen die per turn zowel de eigen `overlap`/`uncertain_assignment`
  als `context_available_before`/`context_uncertain_before` checkt vóórdat een
  oordeel (bv. over gerichte feedback) wordt toegekend.