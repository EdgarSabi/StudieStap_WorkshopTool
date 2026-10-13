# Run 1 versus run 2 — `testaudio2_fragment` (stap 4C, herhaling)

Run 2: `20261012_dev_run2`, identiek aan run 1 (`20261012_dev_run1`): hetzelfde bevroren protocol v1, dezelfde audio-, referentie- en codehashes, hetzelfde git-HEAD `0a4ab99`, dezelfde instellingen, modelrevisies en packages (`run_manifest.json` van beide runs: `inputs`, `pipeline_settings`, `packages`, `hf_snapshots`, `src_sha256` gelijk). Nieuwe inferentie voor alle vier de stappen; geen oude uitvoer hergebruikt. Geen tuning, geen codewijziging.
Ondersteunende bestanden: [run2_artifacts/](run2_artifacts/) (`run1_vs_run2_comparison.json`, `counterexample_output.txt`, run-2-manifest/-resultaat/-scores/-RTTM/-logs). Volledige uitvoer: `Data-local/evaluation/baseline_v1/runs/20261012_dev_run2/testaudio2_fragment/`.
Alle getallen: ontwikkeldata, één fragment, 4,0 s tweede spreker. Geen nauwkeurigheidsclaim.

## 1. Run 1 versus run 2: inhoudelijk identiek

| Onderdeel | Resultaat |
|---|---|
| Stappen | 4/4 ok in beide runs; runtimes 36,9/36,5 s (Whisper), 32,8/32,2 s (pyannote + koppeling), 0,0/0,0 s, 1,74/1,78 s (docent) |
| Whisper | 19 segmenten in beide; tekst, begin, eind, `avg_logprob`, `no_speech_prob`, `compression_ratio`, `quality_flags`: **0 verschillen** |
| Ruwe pyannote | 8 beurten in beide, 2 sprekers; **maximaal grensverschil 0,0 s**; RTTM **byte-identiek** (`cmp`) |
| Sprekerkoppeling | 19/19 segmenten `MAIN_SPEAKER` (`SPEAKER_00`) in beide; `speaker_confidence`, `overlap`, `uncertain_assignment`: 0 verschillen; behouden sprekers na koppeling: `[SPEAKER_00]` in beide |
| Preprocessing | 10 turns in beide, 0 verschillen (grenzen, flags) |
| Rollen | rolreeks identiek (`D D D O D D O D D D`); similarity-verschil **0,0** |
| Scores | van 293 afzonderlijke scorewaarden verschilt er **geen**: WER 0,075 / 0,075; DER-kopcijfer 0,1114 / 0,1114; referentiedekking 10,3 s / 10,3 s; segmentstatus `single 12, mixed 4, no_ref_speech 3` / idem |
| Bestandshashes van de JSON-uitvoer | verschillen, maar uitsluitend door veldwaarden met runtijd en pad (`transcription_time_seconds` 32,21 → 31,89; `runtime_seconds` 20,71 → 20,42; modelladtijden; paden naar de run-map) |

Conclusie H3: voor dit fragment op deze machine is de pipeline in twee runs **bit-reproduceerbaar in alle inhoudelijke velden** (niet weerlegd). Beperking: twee runs, één fragment, dezelfde machine/threads; Whisper-temperatuurfallback is niet gelogd en dus niet uit te sluiten voor andere audio (audio 5 gaf in eerdere runs wel verschillen). Wat de run niet kan bewijzen: reproduceerbaarheid op andere hardware of fragmenten.

## 2. Verdwijnt de tweede spreker opnieuw? Ja, identiek, en hier gaat het mis

Tweede spreker = referentiespreker B (raster-CSV: 4,0 s in 6 rijen; spreker A 18,7 s). Ruwe sprekers (identiek in beide runs): `SPEAKER_00` 29,19 s, `SPEAKER_01` 3,90 s in vier stukjes.

### 2.1 Stap 1 — ruwe diarisatie (pyannote): hier gaat het grootste deel verloren

| Wat | Seconden |
|---|---|
| Referentie-B totaal | 4,0 |
| daarvan binnen een `SPEAKER_01`-interval | **0,62 (15,5 %)** |
| daarvan binnen `SPEAKER_00` (dit overlapt deels met de 0,62) | 3,89 (97 %) |
| daarvan buiten elke ruwe beurt | 0,11 |
| B-rijen **zonder** overlapvlag (1,5 s, "Ruud heeft een brommer", "Ik bedoel, met zijn hond") | **1,5 s volledig in `SPEAKER_00`, 0 s in `SPEAKER_01`** |
| B-rijen met overlapvlag (2,5 s) | 0,62 s in `SPEAKER_01` |
| `SPEAKER_01` totaal 3,90 s: in B / in A / buiten gelabelde spraak | 0,62 / 3,08 / 0,20 |

`SPEAKER_00` loopt bijna doorlopend (0,03–6,66, 6,73–18,49, 18,70–27,30, 27,86–30,05 s) en bevat daarmee vrijwel alle B-spraak. Dit is een **modelfout/clusteringfout van het diarizatiemodel** (B wordt grotendeels bij A gevoegd), niet te herleiden tot de koppeling of de referentie voor de 1,5 s niet-overlappende B-spraak. Of het in pyannote's segmentatienetwerk of in de clustering gebeurt, is **niet vast te stellen** zonder tussenuitvoer van pyannote (niet vastgelegd; zou extra inferentie met instrumentatie vragen).

### 2.2 Stap 2 — koppeling aan Whisper-segmenten (`assign_speakers`): de resterende 0,62 s gaat hier alsnog verloren

| Wat | Resultaat |
|---|---|
| Segmenten gewonnen door `SPEAKER_00` / `SPEAKER_01` | 19 / **0** |
| `SPEAKER_01`-seconden in segmenten waar die verloor | 3,90 van 3,90 (100 %) |
| Grootste aandeel `SPEAKER_01` in één segment | 0,57 (segment 17–18 s), maar `SPEAKER_00` heeft daar 1,00 s |
| Segmenten waar referentie-B > helft van het segment is | segment 4 (7–9 s, B 1,7 s) en segment 9 (15–16 s, B 0,6 s): beide `SPEAKER_00` |

Oorzaak is rekenkundig: de pipeline kiest per segment de spreker met de meeste overlap in tijd. De ruwe beurten van `SPEAKER_00` zijn lang en niet-exclusief; `SPEAKER_01` verschijnt er *bovenop* en heeft daardoor nooit meer seconden dan `SPEAKER_00`. In 7 segmenten is `SPEAKER_01` aanwezig (0,02–1,07 s), in geen enkele wint die. Het gevolg: 5 segmenten krijgen alleen de vlag `overlap=True`; er is geen enkele plek waar de tweede spreker in de uitvoer overblijft.

**Voorbeeld uit de data (segment 7,0–9,0 s):** referentie: B spreekt 7,2–8,9 s ("Nee, maar het gaat ook niet om de brommer"). Ruwe beurten: `SPEAKER_00` 6,73–18,49 s (dekt het hele segment, 2,00 s), `SPEAKER_01` 8,35–10,07 s (0,65 s in het segment, waarvan 0,55 s binnen B). Winnaar `SPEAKER_00`, `overlap=True`, `uncertain_assignment=False`. Hier zijn beide effecten zichtbaar: het model markeert B slechts de laatste 0,55 s van haar beurt, en de koppeling gooit dat weg.

### 2.3 Reproduceerbaar tegenvoorbeeld (zonder modellen)

`counterexample_assign.py` importeert de **ongewijzigde** `assign_speakers`/`build_label_map` en toont (exitcode 0, [uitvoer](run2_artifacts/counterexample_output.txt)):

- (A) herberekening op de echte ruwe beurten en Whisper-segmenten van run 1 *en* run 2 reproduceert de bewaarde uitvoer exact: 19/19 `SPEAKER_00`. De koppeling is dus een deterministische, modelvrije stap waarin `SPEAKER_01` verdwijnt.
- (B1) pyannote vindt B **perfect** (`SPEAKER_00` 0–10 s, `SPEAKER_01` 4–6 s, niet-exclusief) + Whisper-segment 4–6 s → winnaar `SPEAKER_00`.
- (B2) pyannote vindt B perfect en **exclusief** (A 0–4, B 4–6, A 6–10) + één Whisper-segment 2,5–7 s dat de wissel omvat → winnaar `SPEAKER_00` (A 2,5 s tegen B 2,0 s).
- (C) controle: dezelfde exclusieve beurten met Whisper-grenzen die samenvallen (0–4, 4–6, 6–10) → `00, 01, 00`. De functie werkt dus wel; het verlies treedt op door niet-exclusieve beurten en segmenten die een sprekerwissel omvatten.

Commando:

```bash
Data-analysis/src/.venv/Scripts/python.exe -B Data-analysis/Experiments/baseline_evaluation/counterexample_assign.py
```

### 2.4 Referentiebeperkingen (wat niet de pipeline is)

- Overlap is alleen als vlag geannoteerd, zonder tweede spreker. **2,5 van de 4,0 s B (62,5 %)** zit in rijen met `overlap=ja`; in de referentie bestaat daar maar één label.
- 2,52 s van de 3,90 s `SPEAKER_01` (65 %) valt in rijen die de annotator zelf als overlap markeerde (2,1–4,1; 7,2–10,2 s), en de tracked CSV noemt bij 9–11 s "spreker b praat er nog in de achtergrond doorheen" en bij 21–23 s "spreker b maakt geluid in achtergrond". Dat is **consistent met** de mogelijkheid dat een deel van `SPEAKER_01` een echt achtergrondgeluid van B is dat de raster-referentie niet als B-rij bevat; dat is niet vast te stellen zonder luisteren en wordt hier niet aangenomen. Gevolg: de 3,08 s "SPEAKER_01 in A" in 2.1 en het vals alarm in de DER zijn deels een referentiebeperking.
- De gaten (6,4 s) tussen rijen hebben onbekende betekenis; daarom verschilt de DER sterk tussen `labelled` en `strict` (zelfde in beide runs).
- B is slechts 4,0 s; elk getal over B is anekdotisch.

## 3. Verschillen in WER, DER en dekking tussen de runs

Geen: WER 0,075 (9/120) beide runs; DER-raster van 8 varianten identiek; kopcijfer `labelled|exclude|0,25` 0,1114 op 10,3 s referentiespraak (gemist 0,22 / vals alarm 0,43 / verwisseling 0,50 s) in beide; `strict` 0,457–0,658; segmentstatus 12 `single` / 4 `mixed` / 3 `no_ref_speech`. Docentrol: 8 scoorbare turns, 7 goed, 0 ONZEKER, 2 `mixed` ongescoord, in beide. Dekking en onzekerheden zijn dus **stabiel**; de interpretatiebeperkingen uit het run-1-rapport gelden onverkort (o.a. segmentscore 0,857 = aandeel A; docentrol 7/8 = "altijd DOCENT").

## 4. Scheiding van oorzaken (voor dit fragment)

| Laag | Bijdrage | Bewijs |
|---|---|---|
| Diarizatiemodel / clustering | **dominant**: ≥ 3,4 s van 4,0 s B (84,5 %) komt niet in `SPEAKER_01` terecht, inclusief 1,5 s zonder enige overlapambiguïteit; 79 % van `SPEAKER_01` ligt in A-rijen | §2.1; identieke RTTM |
| Alignment (`assign_speakers`) | **dekkend**: wat het model wél als tweede spreker gaf (3,9 s, waarvan 0,62 s in B) verliest 19/19 segmenten; ook bij een perfect model (B1/B2) | §2.2–2.3; deterministisch |
| Referentie | beperkt de **interpretatie**, niet het verlies: 62,5 % van B en 65 % van `SPEAKER_01` ligt in overlapzones met één label; gaten ambigu | §2.4 |

Of de DER-fout een model- of een referentiefout is, kan voor het overlapdeel niet worden beslist zonder tweede-sprekerannotatie of beluistering.

## 5. Gevolgen (geen actie uitgevoerd)

- Vaststaand voor dit fragment: de tweede spreker verdwijnt reproduceerbaar; de pipeline-uitvoer bevat daardoor structureel één spreker, en 4 van 19 segmenten bevatten volgens de referentie twee sprekers.
- Onbeantwoord: of segmentatie of clustering binnen pyannote de oorzaak is; of `SPEAKER_01` deels echte achtergrond-B is; of het patroon zich herhaalt op de andere fragmenten (audio 4 had in eerder werk 4 echte sprekers; dat is niet in dit harnas gemeten).
- Voor een vervolgstap (alleen als jij dat wilt): dezelfde diagnose (§2.1/2.2 via `compare_runs.py`) op de overige ontwikkelfragmenten, zonder instellingen te wijzigen. Het verlies in de koppeling is onafhankelijk van het model aantoonbaar (B1/B2) en dus een ontwerpbeperking die elk ander diarizatiemodel ook zou treffen zolang de koppeling per segment op maximale overlap blijft kiezen.

## 6. Integriteit na run 2

`no_touch_check` van run 2: geen bestand toegevoegd/gewijzigd in `Data-local/processed`, `src/*.py` en alle referentie-CSV's onveranderd. Onafhankelijk herhaald: de hashes van alle `src`-modules, `testaudio2_fragment.mp3`, `testdocent.mp3`, alle ground-truth-CSV's en de drie `*_manual.txt` komen overeen met PROTOCOL §1; geen bestand in `Data-local/processed` is nieuwer dan de runs; `git status` toont uitsluitend ongetrackte bestanden.

## 7. Reproduceren

```bash
Data-analysis/src/.venv/Scripts/python.exe -B Data-analysis/Experiments/baseline_evaluation/compare_runs.py --run-a Data-local/evaluation/baseline_v1/runs/20261012_dev_run1/testaudio2_fragment --run-b Data-local/evaluation/baseline_v1/runs/20261012_dev_run2/testaudio2_fragment --out <nieuw-bestand>.json
```
