# Baseline run 1 — `testaudio2_fragment` (ontwikkelbaseline, stap 4C)

Run-id `20261012_dev_run1` · protocol v1 ongewijzigd · repo `main` @ `0a4ab99` · CPU, offline (`HF_HUB_OFFLINE=1`) · één run, één fragment (30,01 s).
Alle getallen zijn **ontwikkeldata en optimistisch**; geen enkel getal is een nauwkeurigheidsclaim. Er is niets gerepareerd of bijgesteld.

**Uitvoer:** volledig in `Data-local/evaluation/baseline_v1/runs/20261012_dev_run1/testaudio2_fragment/` (gitignored; bevat transcripties van leerlingen). Een kopie van manifest, resultaat, scores, RTTM en logs (zonder transcripties) staat in [run1_artifacts/](run1_artifacts/).

## 1. Uitvoering

| Stap | Status | Tijd | Opmerking |
|---|---|---|---|
| 01 Whisper medium (nl, int8, beam 5, VAD) | ok | 36,9 s (ASR 32,2 s) | 19 segmenten |
| 02 pyannote 3.1 + sprekerkoppeling (geen priors) | ok | 32,8 s (model 20,7 s) | 8 ruwe beurten, 2 ruwe sprekers; log bevat 1 pyannote-`UserWarning` (`std(): degrees of freedom <= 0`), gevolg onbekend |
| 03 preprocessing | ok | < 0,1 s | 19 segmenten → 10 turns, 0 sprekerwissels |
| 04 docentherkenning (drempel 0,35) | ok | 1,7 s | 8× DOCENT, 2× OTHER, 0× ONZEKER |

Fouten/uitzonderingen: geen. Instellingen, hashes, omgeving en modelrevisies: `run_manifest.json`. `no_touch_check`: geen bestand toegevoegd/gewijzigd in `Data-local/processed`, `src/*.py` en alle referentie-CSV's onveranderd.

## 2. Integriteit (onafhankelijk herhaald na de run)

7 `src/*.py`, 5 fragment-mp3's, `testdocent.mp3`, alle 8 ground-truth-CSV's en de 3 `*_manual.txt` hebben nog precies de hash uit PROTOCOL §1. Geen bestand in `Data-local/processed` is nieuwer dan de run. `git status` toont uitsluitend ongetrackte bestanden (geen enkel getrackt bestand gewijzigd). Geen `.pyc` in `src` aangemaakt.

## 3. Metingen en hoe ver ze reiken

**Tekst (WER/CER)** — status *exploratief* (referentie deels Whisper-voorgevuld; tekstrijen overlappen in tijd).
- Tegen de primaire raster-referentie: WER **0,075** (9 fouten op 120 woorden: 5 vervangingen, 3 weglatingen, 1 invoeging; de fouten zijn "opdracht→op de", "dat→dan", "hier→ie", "ik zie→je ziet", "de hele tijd" ontbreekt), CER 0,043. Aarzelgeluiden komen niet voor: variant met en zonder is gelijk.
- Tegen `testaudio2_manual.txt`: WER **0,256** (32/125). De twee menselijke referenties verschillen onderling **0,224** (> 5 %-regel) en worden daarom **niet** samengevoegd. De onzekerheid in de referentie is dus groter dan de gemeten fout; 0,075 zegt alleen: "ligt dicht bij deze ene referentie".
- Circulariteit: 12/19 rijen gelijk aan Whisper (0,63 < 0,90): **niet circulair** volgens de vooraf vastgelegde toets.

**Ruwe DER** (pyannote-beurten; 8 vooraf vastgelegde varianten, hier de uitersten): kopcijfer `labelled | overlap=exclude | collar 0,25` = **0,111** (gemist 0,22 s, vals alarm 0,43 s, verwisseling 0,50 s op slechts 10,3 s referentiespraak). Over alle varianten loopt DER van 0,111 tot 0,658; `strict` (gaten = stilte) is veel hoger door 3,7–11 s vals alarm in niet-gelabelde gebieden, waarvan niet bekend is of het stilte of niet-geannoteerde spraak is. *Exploratief*: te weinig referentiespraak na uitsluiten/collar, onvolledige overlapannotatie, onduidelijke gaten.
- Pyannote vond 2 sprekers (SPEAKER_01 totaal 3,9 s in 4 stukjes), maar daarvan valt slechts **0,62 s in referentiespreker B** en 3,08 s in A (B heeft in de referentie 4,0 s, A 18,7 s). Met één run is dit wat de ruwe diarisatie hier deed; of het stabiel is, is niet getoetst.

**Segmentgebaseerd** — alle 19 Whisper-segmenten kregen `MAIN_SPEAKER` (`speaker_raw` = SPEAKER_00); de tweede ruwe spreker verdwijnt volledig in de koppeling. Van 12 `single`-segmenten (21 s) is 18 s "goed" (**0,857**), maar dat getal is gelijk aan het aandeel van spreker A en dus **geen bewijs van sprekerscheiding** (een systeem dat altijd "A" zegt scoort hetzelfde). 4 segmenten (3, 8, 9, 12; 21 %) hebben twee referentiesprekers (`mixed`) en 3 liggen in referentiestilte. De segmentversie geeft een **lagere** DER (0,176 bij `labelled|keep|0`) dan de ruwe beurten (0,334), omdat één label geen vals alarm kan maken; een lage segment-DER mag dus niet als betere diarisatie worden gelezen.

**Docentrol** — *exploratief*. Van 10 turns zijn 8 scoorbaar (7 docent, 1 leerling), 2 zijn `mixed` (9 s, voorspeld DOCENT, niet gescoord maar getoond). Beslissingsaandeel 8/8, 0 ONZEKER, decided accuracy **7/8 = 0,875**. "Altijd DOCENT" zou ook 7/8 halen; er is maar één leerling-turn; drempel 0,35 is in-sample gekozen op dit fragment. Niet interpreteerbaar als herkenningsprestatie. Eén fout: turn 17–18 s (referentie docent, voorspeld OTHER).

**Kwaliteitswaarschuwing `unintelligible`** — de raster-CSV heeft geen `intelligible`-kolom, dus **niet beschikbaar**. De scores melden "0 rijen" (zie fout 2); er zijn geen rijen uitgesloten.

## 4. Concrete bevindingen

1. **Sprekerkoppeling collapst op dit fragment naar één spreker**; 21 % van de segmenten bevat twee referentiesprekers en kan met één label per segment niet correct zijn. Ontwerpgevolg, geen crash.
2. **Harnas-rapportage:** `quality_warning_unintelligible` toont `rows_ja: 0` voor een bestand zonder die kolom, in plaats van "niet beschikbaar". Niet aangepast (protocol bevroren); moet bij een volgende versie expliciet worden.
3. **Harnas-label te mild:** `der_overlap_exclude` en `segment_eval` krijgen automatisch "indicative", ook als er na uitsluiten slechts 10 s referentiespraak overblijft. In dit rapport behandeld als exploratief.
4. **Referentie-onzekerheid:** gaten (6,4 s) met onbekende betekenis; 6 overlaprijen zonder tweede spreker; raster en manual verschillen 22 %; twee zeer korte rijen (0,1–0,4 s) en een 0,1 s-overlap tussen rij 12 en 13 (uit 4A, nog niet gecontroleerd).
5. Eenmalige pyannote-`UserWarning` in de log; effect niet onderzocht.

## 5. Hypothesen (PROTOCOL §12)

| # | Uitkomst |
|---|---|
| H1 scorers correct | niet weerlegd (52 tests + jiwer-kruiscontrole uit 4B); deze run toont geen tegenvoorbeeld |
| H2 geen bijwerkingen | **niet weerlegd**: `no_touch_check` schoon en onafhankelijk herhaald (§2) |
| H3 zelfde uitvoer bij herhaling | **niet getoetst** met het harnas (geen run 2). Indirect: de 19 Whisper-segmenten zijn tekst- en tijdgelijk aan de oude cache én aan een auditrun; voor pyannote is er geen eerdere ruwe uitvoer om mee te vergelijken |
| H4 raster niet circulair (audio 4/7 wel) | voor audio 2 **bevestigd** (0,63). Audio 4/7 niet in deze run getoetst |
| H5 WER exact 0 duidt op circulariteit | niet weerlegd (WER 0,075, niet 0) |
| H6 ruwe DER toont fouten die in de segmentversie verdwijnen | **niet weerlegd**: 4 `mixed` segmenten en de tweede ruwe spreker die in de koppeling verdwijnt. Wel kwam de omgekeerde verwachting niet uit: de segment-DER is hier lager dan de ruwe DER |

**Geen van de vooraf vastgelegde hypothesen is weerlegd.** Wat de meting wél corrigeert is een impliciete verwachting: dat een segment-DER de diarisatiefouten overschat of gelijk weergeeft; hier maskeert hij ze juist (één spreker = geen vals alarm).

## 6. Antwoorden

- **Heeft de volledige pipeline gewerkt?** Ja, technisch: alle vier de stappen zonder fout, uitvoer compleet en onaangetast. Inhoudelijk werkt de sprekerscheiding op dit fragment niet: de koppeling levert één spreker.
- **Concrete fouten:** zie §4 (collaps naar één spreker; twee harnasrapportage-zwakten; referentie-onzekerheid; pyannote-waarschuwing).
- **Verantwoord interpreteerbaar:** (a) dat de keten draait en reproduceerbaar kan worden vastgelegd; (b) de Whisper-tekst ligt dicht bij de raster-referentie (WER 0,075, 120 woorden) maar de referentie zelf is onzeker (22 % verschil met de andere); (c) het aantal en de verdeling van segmenten met twee sprekers (4 van 19) en dat de ruwe tweede spreker nauwelijks (0,62 s van 3,9 s) op de echte tweede spreker valt. Niet interpreteerbaar: segment-nauwkeurigheid 0,857, docentrol 0,875, alle DER-percentages als kwaliteitsmaat.
- **Welke hypothesen weerlegd?** Geen formeel; zie §5.
- **Overige ontwikkelfragmenten met dezelfde instellingen?** Ja, als dataverzameling, onder voorwaarden: (1) eerst `…_dev_run2` op audio 2 om H3 te toetsen (± 1,5 min); (2) de uitkomsten van audio 4 en 7 WER als "circulair" laten markeren, audio 1 en 5 als extra onzeker lezen; (3) geen conclusies uit enkele percentages, alleen uit tellingen en patronen; (4) de twee harnasrapportage-punten (fout 2 en 3) eerst als protocol v2 vastleggen, zodat de volgende runs onderling vergelijkbaar blijven. Een grote run (audio 4, 120 s) duurt naar schatting 4–5 min.
