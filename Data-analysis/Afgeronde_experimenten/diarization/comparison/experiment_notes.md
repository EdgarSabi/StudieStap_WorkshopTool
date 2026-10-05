# Diarizatie-experimenten: vergelijking

> **Status (bijgewerkt bij reorganisatie): beide experimenten hieronder zijn
> afgerond — we werken er voorlopig niet verder aan. Dat betekent niet dat
> een van beide bewezen onbruikbaar is, alleen dat de productiepipeline
> voorlopig bij BASELINE (pyannote `speaker-diarization-3.1` +
> segment-niveau `assign_speakers()`) blijft.**
> - **A (community-1)** is een alternatief *diarizationmodel* — daarop is de
>   conclusie: **geen overtuigende verbetering aangetoond in onze beperkte
>   tests** (3 korte fragmenten, geen ground truth — zie de tabellen
>   hieronder).
> - **B (WhisperX)** is **geen** alternatief diarizationmodel (het gebruikt
>   hetzelfde pyannote 3.1 als de baseline) — het is een alternatieve
>   **transcriptie/alignment/sprekerkoppelingsroute**: eigen ASR + forced
>   alignment + woordniveau speaker-koppeling, tegen de prijs van een aparte
>   Python-omgeving en aanzienlijk meer dependencies/runtime (zie Tabel 2).
>   De map staat nog op zijn oorspronkelijke plek
>   (`Data-analysis/Experiments/diarization/whisperx/`, incl. eigen venv) —
>   niet verplaatst, wel gemarkeerd als afgerond, niet actief in gebruik.
>   Het lichtere alternatief dat **wel** actief is —
>   `word_timestamps=True` + de bestaande pyannote-turns, zonder WhisperX —
>   staat in
>   [`Experiments/word_level_speaker_attribution`](../../../Experiments/word_level_speaker_attribution).

Vergelijking van drie aanpakken op dezelfde drie testfragmenten
(`testaudio1_fragment`, `testaudio2_fragment`, `testaudio5_fragment`), allemaal
op CPU, Whisper `medium`, taal `nl`.

- **BASELINE**: faster-whisper medium + pyannote `speaker-diarization-3.1` +
  bestaande segment-niveau `assign_speakers()` — de productiepipeline
  ([Data-analysis/src](../../../src)).
- **A**: zelfde ASR-transcript + bestaande `assign_speakers()`, maar pyannote
  `speaker-diarization-community-1` in plaats van 3.1
  ([community1/](../community1)) — alternatief diarizationmodel, geen
  overtuigende verbetering aangetoond in onze beperkte tests.
- **B**: WhisperX (eigen ASR + forced alignment) + pyannote 3.1 (zelfde model
  als baseline) + woordniveau `assign_word_speakers()`
  ([whisperx/](../../../Experiments/diarization/whisperx)) — geen ander
  diarizationmodel, maar een alternatieve transcriptie/alignment/
  sprekerkoppelingsroute; map niet verplaatst (blijft op zijn oorspronkelijke
  plek, zie status hierboven).

> **Belangrijk onderscheid, zoals gevraagd:** diarizatiekwaliteit en
> transcript↔speaker-koppeling zijn twee aparte vragen.
> **(A) Detecteert het diarizationmodel de juiste sprekerwissels?** — dat
> vergelijk je tussen BASELINE en A (zelfde koppel-methode, ander model), en
> onafhankelijk daarvan tussen BASELINE/A en B qua *ruwe* pyannote-turns (B
> gebruikt hetzelfde 3.1-model als de baseline, dus dat deel van B zou
> qua sprekerwissel-detectie identiek moeten zijn aan BASELINE — zie tabel 2).
> **(B) Kan de transcript↔speaker-koppeling die wissels ook terugbrengen in de
> tekst?** — dat is de vraag die alleen B beantwoordt, want dat is het enige
> experiment dat de koppel-methode verandert (woord- i.p.v. segmentniveau).

## Tabel 1 — hoofdvergelijking

| Fragment | Methode | Speakers herkend | Korte wissels in tekst terug te zien? | Mixed-speaker ASR-segment probleem | Overlap-segmenten | Runtime | Opmerking |
|---|---|---|---|---|---|---|---|
| testaudio1 | BASELINE | 3 raw (21 turns) | Nee — "Dit ben jij. Dit ben ik." blijft 1 label | Ja (1 bevestigd geval) | 4/9 | 17.99s | `assign_speakers` kan segment maar 1 label geven |
| testaudio1 | A (community-1) | 2 raw (16 turns) | Nee — zelfde segment, zelfde probleem | Ja (zelfde geval) | 3/9 | 16.47s | Ander diarizationmodel lost het niet op — verwacht, want probleem zit in segmentatie, niet in het diarizationmodel |
| testaudio1 | B (WhisperX) | 3 raw (21 turns, eigen segmentatie) | **Ja** — bv. "Oké," → OTHER_SPEAKER_2, "heel mooi." → MAIN_SPEAKER, binnen 1 ASR-segment | **Opgelost op woordniveau** (2/10 segmenten mixed, correct opgesplitst in `readable_turns`) | n.v.t. (ander koppelmechanisme) | 47.33s (asr 19.9 + align 14.2 + diar 13.3) | Zelfde 3.1-model als baseline qua ruwe turns; verbetering zit in de koppeling, niet het model |
| testaudio2 | BASELINE | 2 raw (8 turns) | Nee — 19/19 segmenten MAIN_SPEAKER | Nee (geen mixed geval gezien) | 5/19 | 19.86s | Diarizatie zelf detecteert amper wissels hier |
| testaudio2 | A (community-1) | 2 raw (8 turns) | Nee — identiek aan baseline | Nee | 5/19 | 17.26s | Geen verbetering — bevestigt dat dit een diarizatie-probleem is, niet een segmentatieprobleem |
| testaudio2 | B (WhisperX) | 2 raw (8 turns) | Nee — `readable_turns` blijft ook hier vrijwel 1 lange MAIN_SPEAKER-beurt (0/21 mixed) | Nee (0/21 mixed) | n.v.t. | 49.76s (28.9+6.9+14.0) | Bevestigt: woordniveau-koppeling helpt niet als de onderliggende diarizatie zelf al geen wissel ziet |
| testaudio5 | BASELINE | 5 raw (23 turns) | Deels — veel korte turns, maar geen ground truth om te checken | Niet expliciet gecheckt | 4/21 | 31.00s | Vlakke verdeling (max 34.9%) — geen dominante spreker, twijfelachtig of MAIN/OTHER-label hier zinvol is |
| testaudio5 | A (community-1) | 3 raw (21 turns) | Deels | Niet expliciet gecheckt | 4/21 | 27.64s | Groepeert 5→3 sprekers — onduidelijk of dat correcter is zonder ground truth |
| testaudio5 | B (WhisperX) | 5 raw (23 turns, eigen segmentatie) | Ja, zeer korte (soms 1 woord) wissels zichtbaar in `readable_turns` | Ja (3/14 mixed) | n.v.t. | 59.18s (27.0+8.4+23.8) | Plausibel gezien de beschrijving (rumoerig, overlap), maar niet geverifieerd |

## Tabel 2 — runtime & complexiteit

| | BASELINE | A (community-1) | B (WhisperX) |
|---|---|---|---|
| Nieuwe dependencies | geen (al aanwezig) | **geen** (zelfde `pyannote.audio==4.0.7`) | volledig aparte venv: torch 2.8.0+cpu, pyannote.audio 4.0.7 (zelfde versie, andere install-bron), ctranslate2, nltk, transformers, ... (103 pakketten, zie `requirements-whisperx.txt`) |
| Losse Python-omgeving nodig? | — | nee | **ja** (Python 3.12, hoofd-venv is 3.14) |
| Diarizatie-runtime (3 fragmenten samen) | 68.9s | 61.4s | 51.0s (diarizatie-deel alleen) |
| Totale runtime incl. ASR (3 fragmenten) | n.v.t. (ASR al gedaan, transcript hergebruikt) | n.v.t. (idem) | **156.3s** (asr+align+diarize samen) |
| Codewijzigingen aan bestaande pipeline | — | 0 regels | 0 regels |
| Nieuwe modules | — | 1 script (`community1_test.py`, ~150 regels, hergebruikt bijna alles) | 1 script (`whisperx_test.py`, ~250 regels, deels nieuwe logica voor woord-reconstructie) |

## Antwoord op de 5 onderzoeksvragen

1. **Worden korte docent-leerlingwissels beter herkend?**
   Door het diarizationmodel zelf: gemengd resultaat. Community-1 vindt
   *minder* ruwe sprekers dan 3.1 op alle drie fragmenten (2 vs 3, 2 vs 2,
   3 vs 5) — dat kan "opschoning van valse sprekers" zijn, of "twee sprekers
   onterecht samenvoegen". Zonder ground truth-annotatie is dit niet hard te
   maken. WhisperX gebruikt hetzelfde 3.1-model, dus qua *modeldetectie* geen
   verschil met de baseline — de winst zit elders (zie vraag 2/3).

2. **Worden woorden beter aan de juiste spreker gekoppeld?**
   **Ja, aantoonbaar** bij WhisperX: `speaker_confidence`/overlap-vlaggen in de
   baseline signaleren al dát een segment onzeker/gemengd is (bv.
   testaudio1 9.52–11.64s: `overlap=True`, `speaker_confidence=0.7377`), maar
   kunnen het niet oplossen. WhisperX's woordniveau-koppeling doet dat wel:
   in `testaudio1_fragment_whisperx_normalized.json` zie je individuele
   woorden binnen één ASR-segment naar verschillende sprekers gaan (`"Oké,"`
   → OTHER_SPEAKER_2, `"heel mooi."` → MAIN_SPEAKER).

3. **Wordt het mixed-speaker-ASR-segment-probleem opgelost?**
   **Ten dele, en alleen door WhisperX (Experiment B), niet door een ander
   diarizationmodel (Experiment A).** Community-1 (A) laat het exact dezelfde
   segment/label-probleem zien als de baseline — logisch, want `A` verandert
   niets aan hoe segmenten aan sprekers gekoppeld worden, alleen wélk
   diarizationmodel de ruwe turns levert. WhisperX (B) lost het gedeeltelijk
   op door zelf op woordniveau te werken, ongeacht welke ASR-segmentgrenzen
   er zijn — maar de segmentgrenzen zelf blijven ook bij WhisperX soms een
   mix bevatten (2/10, 0/21, 3/14 mixed segmenten in de drie fragmenten); het
   is de `readable_turns`-reconstructie die dat oplost voor leesbare tekst,
   niet het ASR-segment zelf.

4. **Hoeveel extra complexiteit, runtime en dependencies?**
   Zie Tabel 2. Community-1 (A) is vrijwel gratis: geen nieuwe dependencies,
   iets sneller dan 3.1 op deze fragmenten, en de code is een dunne wrapper
   om bestaande modules. WhisperX (B) is een substantiële istap: een volledig
   aparte venv/Python-versie, ~100 extra pakketten, en 2-3× de runtime van de
   baseline-diarizatie omdat het zijn eigen ASR + alignment ook nog draait
   (die ASR-tijd zit al niet meer in de baseline-vergelijking, want die
   hergebruikt het bestaande transcript).

5. **Praktisch genoeg voor het prototype?**
   - **A (community-1)**: praktisch gezien een bijna kosteloze swap — zou
     zonder veel moeite de standaard kunnen worden als de kwaliteit
     (met een echte ground-truth-check) beter blijkt. Vereist wel een
     losse beslissing over 5→3-clustering bij testaudio5 (mogelijk
     `min_speakers`/`max_speakers`-priors nodig).
   - **B (WhisperX)**: lost een reëel probleem op (woordniveau-koppeling),
     maar tegen aanzienlijke kosten: aparte omgeving, veel meer dependencies,
     hogere runtime, én een (nog niet doorgronde) tekst-encoding-bug die
     `é`/`ë` corrumpeert — dat laatste is een **blokkerend** kwaliteitsprobleem
     voor een Nederlandstalig prototype, los van hoe goed de
     speaker-koppeling is. Niet direct inzetbaar zonder dat op te lossen of
     te omzeilen (bv. door WhisperX alleen voor alignment+diarizatie te
     gebruiken op een extern, correct getranscribeerd transcript — een
     hybride die dit experiment niet getest heeft).

## Belangrijkste bevinding

De kernvraag van dit hele experiment — "lost een beter diarizationmodel het
mixed-speaker-segment-probleem op?" — beantwoordt Experiment A met **nee**, en
Experiment B laat zien dat het antwoord zit in **hoe** je sprekers aan tekst
koppelt (woord- vs. segmentniveau), niet in **welk** diarizationmodel je
gebruikt. Dat is een bruikbaar inzicht voor de vervolgkeuze: als dit probleem
opgelost moet worden, is de investering in woordniveau-alignment (WhisperX of
een lichtere eigen implementatie met alleen `word_timestamps=True` in
faster-whisper + de bestaande pyannote-turns) waarschijnlijk effectiever dan
het wisselen van diarizationmodel.

## Bekende beperkingen van deze vergelijking

- Geen handmatige ground-truth-annotatie (wie spreekt wanneer) voor een van de
  drie fragmenten — alle "beter/slechter"-uitspraken zijn gebaseerd op wat
  aannemelijk klinkt bij het lezen van de output, niet op een geverifieerde
  referentie. Voor een scriptie-onderbouwing is een klein handmatig
  geannoteerd fragment een logische vervolgstap.
- Kleine steekproef: 3 korte fragmenten (30-46s), niet representatief voor
  een volledige workshopopname (30-60 min) qua runtime-schaling of
  drift-gedrag.
- WhisperX's eigen ASR-segmentatie wijkt af van de baseline, waardoor een
  exacte segment-voor-segment vergelijking niet mogelijk was — vergeleken is
  op het niveau van de uiteindelijke doorlopende (`readable_turns`) tekst.
