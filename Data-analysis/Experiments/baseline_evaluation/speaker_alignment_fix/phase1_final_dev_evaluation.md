# Fase 1 — laatste ontwikkeltests: `testaudio4_fragment` en `testaudio5_fragment`

Branch `feature/lossless-speaker-intersections`, HEAD `afefb0a6866f4d5342d2f4ab67777f24e4b4f1cc` (productiecode identiek aan commit `00f3bda`), werkboom (tracked) schoon, geen merge. Run-ID `20261013_final_dev_run1` (nieuwe, geïsoleerde mappen per fragment onder `Data-local/evaluation/baseline_v1/runs/`; gitignored, bevat transcripties). Verwachtingen vooraf vastgelegd in [final_dev_preregistration.md](final_dev_preregistration.md). Controlescript [final_dev_checks.py](final_dev_checks.py) (+ [replay_original.py](replay_original.py)); resultaten [audio 4](final_dev_checks_testaudio4_output.txt) / [audio 5](final_dev_checks_testaudio5_output.txt) (`.json` ernaast); kopie van manifest, resultaat, scores, RTTM en logs in [final_dev_artifacts/](final_dev_artifacts/).
Instellingen: Whisper medium, pyannote 3.1 **zonder speaker-priors** (`min/max_speakers=None`), alle drempels ongewijzigd. Geen tuning, geen andere modellen.

## 1. Technische uitvoer

| | Whisper | pyannote + koppeling | preprocessing | docent | totaal | status |
|---|---|---|---|---|---|---|
| audio 4 (120,0 s) | 142,5 s | 107,0 s | < 0,1 s | 3,7 s | ≈ 253 s | 4/4 ok |
| audio 5 (46,0 s) | 76,1 s | 44,3 s | < 0,1 s | 2,0 s | ≈ 123 s | 4/4 ok |

Geen fouten of uitzonderingen. `no_touch_check` beide runs schoon. Audio- en referentiehashes gelijk aan PROTOCOL §1.

## 2. De vier verwachtingen: geen enkele weerlegd

| # | Verwachting | audio 4 | audio 5 |
|---|---|---|---|
| E1 | elk (ruwe beurt, segment)-paar met positieve overlap staat als juiste intersection in het segment (onafhankelijke exacte rationale berekening, tolerantie 10⁻¹²) | **170 paren, 0 afwijkingen** | **41 paren, 0 afwijkingen** |
| E2 | meerdere ruwe sprekers per segment blijven zichtbaar na preprocessing, docentstap en JSON-herladen | vlag consistent; 70 turns, turnsamenvatting = som bronsegmenten; herladen ok | idem (17 turns) |
| E3 | dominant label en bestaande functionaliteit ongewijzigd, getoetst door de **originele** code (`0a4ab99`) op dezelfde nieuwe ruwe beurten en Whisper-segmenten te herhalen | 87 segmenten en 70 turns identiek in alle bestaande velden | 24 segmenten en 17 turns identiek |
| E4 | korte activiteit en rumoer: elk ruw label met activiteit binnen een segment blijft in de intersections | 25 ruwe beurten < 1 s (kleinste 0,017 s): alle bewaard | 14 beurten < 1 s (kleinste 0,017 s): alle bewaard |

13/13 controles per fragment (incl. integriteit). De E3-replay vermijdt het vergelijkbaarheidsprobleem met oude uitvoer: oude en nieuwe code krijgen exact dezelfde ruwe invoer. Docentrollen zijn niet opnieuw "met oude code" berekend (`docent_recognition.py` is ongewijzigd); wel is aangetoond dat de docentstap geen turnveld buiten zijn eigen rolvelden wijzigt en dat zijn invoer (de legacy-turnvelden) identiek is aan die van de originele code.

**Vergelijking met oude uitvoer is alleen diagnostisch.** Audio 4: Whisper nu identiek aan de oude cache én de auditrun (87/87 segmenten, tekst en tijden). Audio 5: Whisper nu **24 segmenten**, de oude cache en de auditrun hebben 21 (en onderling verschilden die al in 9 van 21) — Whisper is op deze rumoerige opname niet stabiel over runs. De oude diarisatiecaches zijn om die reden en door andere priors/codeversie niet als vergelijking gebruikt.

## 3. Sprekeraantallen

| | audio 4 | audio 5 |
|---|---|---|
| Referentie: bekende sprekers (spreektijd) | 4: A 72,0 s, B 36,9 s, **C 7,3 s, D 0,8 s** | 3: A 11,7 s, B 17,1 s, C 8,4 s (+ 2 `ONBEKEND`-rijen, 1 afgekapte rij) |
| Ruwe pyannote-sprekers | **2** (`SPEAKER_00` 81,7 s, `SPEAKER_01` 49,6 s; 63 beurten) | **5** (10,9 / 6,0 / 15,8 / 9,9 / 2,6 s; 23 beurten) |
| Segmenten / dominante labels | 87 / 2 (54× `_00`, 33× `_01`) | 24 / 5 (8, 6, 4, 4, 2) |
| Turns / dominante turnlabels | 70 / 2 | 17 / 5 |
| Segmenten met meerdere ruwe sprekers (nieuw) | **57 van 87** | **11 van 24** |
| Turns met meerdere ruwe sprekers (nieuw) | 56 van 70 | 11 van 17 |
| Legacy-`overlap`-vlag | 39 segmenten (allemaal ook `multiple`; 18 `multiple` zonder overlapvlag) | 7 (allemaal ook `multiple`; 4 zonder) |
| Docentrol DOCENT / OTHER / ONZEKER | 20 / 16 / **34** | 2 / 10 / 5 |

## 4. Behouden en verloren sprekerintervallen

- **Binnen de segmenten gaat niets verloren** (E1/E4): alle 170 + 41 paren staan er, inclusief slivers tot 0,017 s en beurten in het rumoerige slot van audio 4 (laatste ≈ 7 s).
- **Buiten de segmenten staat per constructie niets in de segmentinformatie**: geen enkele ruwe beurt ligt geheel buiten alle segmenten; wel valt een deel van beurten buiten: audio 4 0,2 s per label; audio 5 `SPEAKER_00` 0,72 s, `_01` 0,06 s, `_02` 0,83 s, `_03` 0,79 s, `_04` 0,01 s (samen 2,4 s). Dit staat alleen in de RTTM.
- **Dominant verlies bestaat niet meer als informatieverlies:** audio 5 heeft nu alle 5 ruwe labels ook als dominant label; audio 4 beide. Bij audio 4 is de winst van de uitbreiding daarom beperkt tot het kunnen zien *waar* een tweede label meeloopt, niet tot het terugvinden van een verloren label.

## 5. Tegenvoorbeelden en concrete fouten

1. **De zeer korte vierde spreker is upstream verloren, niet in de koppeling.** Referentie-D (111,8–112,6 s, 0,8 s) valt 100 % in ruwe `SPEAKER_01` (de spreker die ook B bevat); er bestaat geen derde of vierde ruw label. Referentie-C (7,3 s) zit voor 2,5 s in `_00` en 7,1 s in `_01`. De uitbreiding kan geen sprekers terugvinden die pyannote nooit afscheidde.
2. **Over- en ondersplitsing:** audio 4 → 2 ruwe sprekers voor 4 referentiesprekers; audio 5 → 5 ruwe voor 3 bekende. In audio 5 verdeelt referentie-B zich over alle vijf ruwe labels (3,8 / 1,9 / 3,8 / 5,7 / 1,8 s) en C over drie (2,0 / 4,1 / 0,7 s); A zit 10,6 van 11,7 s in `_02`. Dit is een eigenschap van het diarizatiemodel op rumoerige opnames.
3. **`multiple_raw_speakers` is te weinig selectief om als enige indicator te dienen:** 57/87 (audio 4) en 11/24 (audio 5) segmenten krijgen de vlag; bij 13 (audio 4) en 4 (audio 5) bestaat de "tweede spreker" uit minder dan 0,1 s. Er is bewust geen drempel; consumenten moeten de duur gebruiken (mediaan minderheidsspraak 0,325 s; ≥ 0,5 s in 20 resp. 5 segmenten).
4. **Referentie kan meerdere sprekers per segment niet uitdrukken:** `segment_eval` meldt voor audio 5 `mixed = 0` terwijl 11 segmenten meerdere ruwe labels bevatten, en voor audio 4 `single = 87`: de referentierijen volgen de Whisper-segmentgrenzen (audio 4: 100 % op het ASR-raster).
5. **Referentiespraak zonder ruwe beurt** (gemiste spraak door pyannote): audio 4 A 7,29 s, B 1,45 s, C 0,15 s; audio 5 A 1,09 s, B 1,96 s, C 1,64 s. Een bestaande beperking, onveranderd.
6. **Hoge onzekerheid in de docentstap:** audio 4: 34 van 70 turns `ONZEKER`.
7. **Bekende harnaszwakte (ongewijzigd):** de `unintelligible`-waarschuwing meldt "0 rijen" voor audio 4, waar die kolom leeg is (niet beschikbaar). Audio 5: 4 rijen / 9,9 s `ja` (alleen waarschuwing, niets uitgesloten).

Actief gezocht naar regressies en verliezen (zeer korte beurten, slivers, rumoerig slot, ruwe labels zonder dominant segment, buiten-segment-activiteit): **geen verlies binnen segmenten en geen verandering van een bestaand veld gevonden.**

## 6. Scores en dekking (alleen binnen de vooraf vastgelegde beperkingen; dev, optimistisch)

| | audio 4 | audio 5 |
|---|---|---|
| WER/CER | **niet rapporteren**: circulair (87/87 rijen = Whisper; WER 0,000) | exploratief: WER 0,087 tegen de CSV (15/19 rijen = Whisper), 0,280 tegen `testaudio5_manual.txt`; de twee referenties onderling 0,313 → geen enkele WER is een nauwkeurigheidsclaim |
| Ruwe DER, kopcijfer `labelled|exclude|0,25` | 0,278 op 70,1 s referentiespraak (gemist 4,3 / vals alarm 9,2 / verwisseling 6,0 s); bereik over 8 varianten 0,278–0,391. *Exploratief*: referentie op ASR-raster; 2 ruwe tegen 4 referentiesprekers | 0,282 op 22,3 s (gemist 2,1 / vals alarm 0,0 / verwisseling 4,2 s); bereik 0,282–0,553. *Exploratief*: `ONBEKEND`-gebieden gemaskeerd, 4 overlaprijen zonder tweede spreker |
| DER op segmentniveau (hypothese = `speaker_raw`) | 0,136 — lager dan de ruwe DER omdat ruwe tracks vals alarm (9,2 s) geven; niet te lezen als betere diarisatie | n.v.t. in dit rapport |
| Segmentnauwkeurigheid (seconden, `single`) | 0,803 over 87 segmenten (2 labels voor 4 sprekers) | 0,603 over 20 `single`-segmenten (4 `masked`) |
| Docentrol | geen rolreferentie → niet gescoord | 13 scoorbare turns, 11 beslist (2 ONZEKER), beslist-juist 11/11, docent-turns n = 2 → **niet interpreteerbaar** (drempel in-sample) |

## 7. Conclusie

**Wat fase 1 heeft aangetoond (voor deze drie ontwikkelfragmenten):**
- De uitbreiding bewaart ruwe sprekerintervallen verliesloos *binnen* de Whisper-segmenten: 170 + 41 (ruwe beurt, segment)-paren op audio 4 en 5 en alle 19 segmenten van audio 2, 0 afwijkingen ten opzichte van een onafhankelijke exacte berekening, ook voor sliver- en rumoerintervallen.
- Ze verandert niets aan bestaande uitvoer: dominante labels, segmentvelden, turns en rolinvoer zijn identiek aan wat de originele code op dezelfde invoer levert (audio 4, audio 5) en aan de baseline (audio 2).
- De informatie overleeft preprocessing, docentstap en JSON-herladen.
- De pipeline draait reproduceerbaar en zonder bijwerkingen op bestaande bestanden; het evaluatieharnas legt invoer, instellingen, hashes en uitvoer vast.

**Wat fase 1 niet heeft aangetoond:**
- Geen nauwkeurigheid van Whisper, pyannote of docentherkenning: de referenties zijn Whisper-voorgevuld (audio 4 volledig circulair), kort, van één opnameserie, en alle fragmenten zijn ontwikkeldata die al voor keuzes zijn gebruikt. Er is geen achtergehouden testset.
- Geen verbetering van sprekerherkenning: de wijziging voegt informatie toe, maar vindt geen sprekers die pyannote niet scheidt (zie D en C) en lost geen over- of ondersplitsing op.
- Niet dat een ruw label een fysieke persoon is, en niet welke ruwe labels bij echte overlap horen (referentie heeft alleen een overlapvlag).
- Geen woordniveau-toewijzing en geen oplossing voor "één label per tekstsegment"; geen consument gebruikt de nieuwe velden al.
- Reproduceerbaarheid van Whisper is niet gegarandeerd (audio 5: 24 tegenover 21 segmenten); van pyannote is ze alleen op audio 2 getoetst (identiek in twee runs).

## 8. Openstaande beperkingen voor de volgende fase

1. Achtergehouden testset zonder Whisper-voorinvulling, met volledige overlapannotatie (tweede spreker) en sprekerrollen voor audio 4.
2. Diarizatiemodel: 2 van 4 resp. 5 van 3 sprekers; kleine sprekers (0,8 s, 7,3 s) en rumoer. Oorzaak binnen pyannote (segmentatie vs clustering) niet vastgesteld; geen tussenuitvoer vastgelegd.
3. Consumenten van de nieuwe velden ontbreken (docentherkenning op turnniveau, classificatie, `segment_eval`); `multiple_raw_speakers` heeft een gebruiksregel op basis van duur nodig (nu bewust geen drempel).
4. Splitsing van segmenten/turns bij sprekerwissel (woord-timestamps) is een aparte ontwerpstap.
5. Whisper-instabiliteit op rumoerige audio (audio 5) en de ruwe activiteit buiten Whisper-segmenten (2,4 s in audio 5).
6. Protocol v2: nieuwe `src`-hashes, `unintelligible` als "niet beschikbaar" bij ontbrekende kolom, en een expliciete minimale hoeveelheid referentiespraak voor het label "indicatief".
7. Docent-`ONZEKER` is hoog bij veel korte/overlappende turns (audio 4: 34/70); herkomst en dekking van `testdocent.mp3` nog niet nagegaan.

## 9. Integriteit

Broncode: huidige hashes = runmanifests (`diarization.py` `364196b8…`, `models.py` `102232b4…`, `preprocessing.py` `6248979d…`); `git status` (tracked) schoon; `HEAD` ongewijzigd. Audio en referenties: hashes gelijk aan PROTOCOL §1. Uitvoerhashes van alle vijf runs (audio 2 baseline run 1 en 2, audio 2 voor/na-run, audio 4 en 5) nog gelijk aan hun `run_result.json` (25 bestanden). `Data-local/processed`: ongewijzigd (no_touch_check in beide runs). Ground truths, modellen, drempels en instellingen niet gewijzigd.
