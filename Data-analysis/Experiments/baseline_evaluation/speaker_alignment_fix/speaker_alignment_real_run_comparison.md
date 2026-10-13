# Echte voor/na-test — verliesloze sprekerintervallen (`testaudio2_fragment`)

Run-ID `20261013_lossless_run1` · branch `feature/lossless-speaker-intersections` · **geteste HEAD `afefb0a6866f4d5342d2f4ab67777f24e4b4f1cc`** · één fragment, één run, geen merge, geen tuning.
Volledige uitvoer: `Data-local/evaluation/baseline_v1/runs/20261013_lossless_run1/testaudio2_fragment/` (gitignored; bevat transcripties). Kopie van manifest, resultaat, scores, RTTM en logs: [real_run_artifacts/](real_run_artifacts/). Controles: [real_run_comparison_output.txt](real_run_comparison_output.txt), [real_run_comparison_checks.json](real_run_comparison_checks.json), script [compare_real_run.py](compare_real_run.py).

## 0. Conclusie: **GESLAAGD**

Alle 32 controles slagen; er is geen afwijking in de bestaande functionaliteit en geen verlies van ruwe sprekerinformatie gevonden. Beperking van het bewijs: één fragment, één run op dezelfde machine, en de modeluitvoer was identiek aan de baseline — de test laat dus zien dat de code niets verandert en alles bewaart bij *deze* invoer, niet hoe de code zich gedraagt bij andere modeluitvoer.

## 1. Afwijking van de opdracht vooraf (gemeld, geen invloed)

De opdracht noemt commit `00f3bda…`. `HEAD` is `afefb0a…` ("Tests van Chat en Claude"), een latere commit op dezelfde branch die alleen documentatie, het evaluatieharnas, testuitvoer, de raster-CSV en `Interview_Melle.docx` toevoegt. `git diff 00f3bda HEAD -- Data-analysis/src` is **leeg**: de productiecode is identiek. Branch staat gelijk met `origin/feature/lossless-speaker-intersections`; werkboom schoon.

## 2. Technische status

| Stap | Status | Tijd (nieuw / baseline run 1) |
|---|---|---|
| 01 Whisper medium | ok | 41,4 s / 36,9 s |
| 02 pyannote 3.1 + koppeling | ok | 34,4 s / 32,8 s |
| 03 preprocessing | ok | < 0,1 s / < 0,1 s |
| 04 docentherkenning | ok | 1,3 s / 1,7 s |

Geen fouten of uitzonderingen. `no_touch_check`: niets toegevoegd of gewijzigd in `Data-local/processed`, `src/*.py` en referenties. Runtimeverschillen (Whisper +4,5 s) komen uit de modelstappen, niet uit de gewijzigde code; niet verder onderzocht. Instellingen, modelrevisies en packages gelijk aan de baseline; nieuwe broncodehashes staan in het nieuwe `run_manifest.json` (`diarization.py` `364196b8…`, `models.py` `102232b4…`, `preprocessing.py` `6248979d…`). `PROTOCOL.md` en de baselinemanifests zijn niet aangepast.

**Evaluatieharnas:** hoefde niet gewijzigd te worden. De stappen schrijven hun JSON via de productiemodellen, dus de nieuwe velden staan in `*_diarized.json`, de preprocessing- en de docentuitvoer (gecontroleerd in G5/I1/I2). `score_run.py` leest de nieuwe velden niet en heeft ze niet nodig: de scores zijn identiek.

## 3. Voor/na-vergelijking

Onderscheid: **modeluitvoer** (Whisper, pyannote) versus **effect van de codewijziging**.

| Vraag | Resultaat | Check |
|---|---|---|
| Whisper-uitvoer (modelverschil?) | **identiek**: 19 segmenten, alle velden gelijk aan run 1 én run 2 | B1 |
| Ruwe acht pyannote-beurten (modelverschil?) | **identiek** aan run 1; RTTM byte-gelijk aan run 1 en 2 (`24ce70f0…`) | C1, C2 |
| 19 dominante sprekerlabels identiek? | **ja**: 19× `SPEAKER_00` / `MAIN_SPEAKER`; ook `speaker_confidence`, `overlap`, `uncertain_assignment`, tekst, tijden en kwaliteitsmaten gelijk | D1, D2, D3 |
| Tien turns identiek in bestaande velden? | **ja**: grenzen, tekst, speaker, flags, context, bron-indices, bronsegmenten; preprocessing-configuratie gelijk | E1, E2 |
| Extra intersections in de 7 segmenten bewaard? | **ja**: segmenten 1, 4, 5, 11, 12, 15, 16 hebben `multiple_raw_speakers=True`; alle andere 12 niet | F2 |
| Zijn alle intersections correct? | **ja**: aantal, label, begin, eind en duur van alle 19 segmenten gelijk aan een onafhankelijke berekening met exacte rationale getallen (tolerantie 10⁻¹²) en aan de eerdere replay | F1, F5 |
| `SPEAKER_01` ≈ 3,898125 s? | **3,898125 s** in de intersections (= totaal ruwe `SPEAKER_01`); `SPEAKER_00` 29,142156 s binnen de segmenten | F3 |
| Na preprocessing aanwezig? | **ja**: `SPEAKER_01` in turns 1 (0,726 s), 3 (0,650), 4 (1,072), 6 (0,571), 7 (0,292), 8 (0,588); samen 3,898125 s; per turn gelijk aan de bronsegmenten | G1, G2 |
| WER, DER, segment- en rolscores gelijk? | **ja**: alle scorewaarden gelijk aan run 1 (WER 0,075; DER-kopcijfer 0,1114) | H1 |
| Docentrollen gelijk? | **ja**: `D D D O D D O D D D`, similarities en noten gelijk; nieuwe velden blijven in de rolluitvoer behouden | G3–G5 |
| Na JSON-herladen aanwezig? | **ja**: `WorkshopTranscript` en `ProcessedTranscript` (preprocessing en rolluitvoer) herladen en opnieuw geserialiseerd zonder verlies | I1, I2 |

Intersections in de zeven segmenten (begin–eind in s; dominant blijft `SPEAKER_00`):

| Segm. | Tijden | `SPEAKER_00` | `SPEAKER_01` |
|---|---|---|---|
| 1 | 2,0–4,0 | 2,0–4,0 (2,000) | 2,984–3,710 (0,726) |
| 4 | 7,0–9,0 | 7,0–9,0 (2,000) | 8,350–9,000 (0,650) |
| 5 | 9,0–11,0 | 9,0–11,0 (2,000) | 9,000–10,072 (1,072) |
| 11 | 17,0–18,0 | 17,0–18,0 (1,000) | 17,429–18,000 (0,571) |
| 12 | 18,0–19,0 | 18,000–18,492 en 18,695–19,000 (0,492 + 0,305) | 18,000–18,020 (0,020) |
| 15 | 21,0–23,0 | 21,0–23,0 (2,000) | 22,728–23,000 (0,272) |
| 16 | 23,0–25,0 | 23,0–25,0 (2,000) | 23,000–23,588 (0,588) |

**Alleen veranderd door de codewijziging:** de nieuwe velden. In de gediarizeerde en verwerkte JSON zijn dat de intersections en vlaggen; in het Whisper-transcript-JSON staan nu ook de nieuwe velden, maar uitsluitend als lege standaardwaarde (`[]`/`False`; schema-gevolg, geen modelverschil). **Veranderd door de modeluitvoer:** niets.

## 4. Actieve falsificatie

- **Tegenvoorbeeldzoektocht** (F4) over alle 19 segmenten: geen intersection buiten segmentgrenzen; duur = eind − begin; altijd gesorteerd; het dominante label altijd aanwezig; geen segment zonder intersections; `multiple_raw_speakers` altijd consistent met de lijst; elk segment met `overlap=True` heeft ook `multiple_raw_speakers=True`. **0 gevonden.**
- **Zelftest van de controle:** op een tijdelijke gemanipuleerde kopie (SPEAKER_01 uit segment 4 verwijderd en vlag gewist; dominant label van segment 3 gewijzigd) falen 10 controles (D1, D2, F1–F5, I1, I2×2); de controle ziet dus verlies en wijziging ([uitvoer](real_run_comparison_tamper_selftest.txt)).
- **Fouten in mijn eerste vergelijkingsscript** (niet in de pipeline): een `KeyError` bij een turn zonder `SPEAKER_01`, een tuple/lijstvergelijking, en B1 negeerde nog niet dat het transcript nu lege nieuwe velden bevat. Alleen het script is aangepast; de run zelf is niet opnieuw gedraaid. Afgerond resultaat: 32/32.
- **Regressies of tegenvoorbeelden in de pipeline: geen gevonden.**

Waarneming, geen fout: segment 12 krijgt `multiple_raw_speakers=True` door 0,020 s `SPEAKER_01` (18,000–18,020 s); er is bewust geen drempel, dus de duur moet door consumenten worden gebruikt (bekend uit het eerdere rapport).

## 5. Integriteit

- Audio (`3f5aaf74…`), rasterreferentie (`4b2a9932…`), rolbron, handmatige tekst en docentreferentie: hashes gelijk aan de oorspronkelijke baselines (A3, J4).
- Baselinerun 1 en 2: alle opgeslagen uitvoerhashes nog gelijk aan hun `run_result.json` (J3); hun manifests en `PROTOCOL.md` ongewijzigd.
- Broncode: huidige hashes gelijk aan het nieuwe runmanifest en aan de commit (J1, J2); alleen `models.py`, `diarization.py` en `preprocessing.py` verschillen van de baseline-hashes (A6).
- `Data-local/processed` (oude caches): niet gelezen als meting en niet gewijzigd (A2).
- Ground truths: niet gewijzigd; werkboom schoon (J1).

## 6. Beperkingen

- Eén fragment (30 s), één run; de uitkomst bewijst geen gedrag bij andere diarizatie-uitvoer of andere audio (daar dekken de 40 unit-tests de logica, niet de data).
- "Verliesloos" geldt voor intersections *binnen* de Whisper-segmenten; activiteit buiten de segmenten staat alleen in de ruwe RTTM.
- De test toont niet dat `SPEAKER_01` de tweede persoon is; WER, DER en docentrollen zijn per definitie gelijk gebleven en niet verbeterd.
- De informatie wordt door geen stap nog gebruikt (docentherkenning, classificatie, scorers).
