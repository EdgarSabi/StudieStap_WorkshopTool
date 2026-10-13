# Correctie na onafhankelijke review — oude intersections bij hernieuwd koppelen

Branch `feature/lossless-speaker-intersections` (ongewijzigd, **geen commit**). Aanleiding: `speaker_alignment_independent_review.md` (oordeel "eerst corrigeren"). Alleen de ene aangetoonde fout is gecorrigeerd; de overige punten uit de review (o.a. duplicaten/duursemantiek in de turnsamenvatting) zijn bewust niet aangeraakt. Geen modelrun; geen wijziging van instellingen, drempels, ground truths, baselineruns of andere functionaliteit.

## 1. De fout (reproduceerd en bevestigd)

In `assign_speakers` zet de tak `if not per_speaker or duration <= 0` met `model_copy(update=…)` alleen `speaker`, `speaker_raw`, `speaker_confidence`, `overlap` en `uncertain_assignment`. `model_copy` behoudt niet-bijgewerkte velden. Werd een eerder verrijkt segment opnieuw gekoppeld met lege, niet-overlappende of ongeldige invoer, dan bleven `raw_speaker_intersections` en `multiple_raw_speakers` van de vorige koppeling staan, en preprocessing rapporteerde nog oude `raw_speaker_seconds`. Bewijs: zonder de correctie falen de nieuwe tests (zie §3), met dezelfde assertion-melding "oude intersections bleven achter".

## 2. De correctie ([diarization.py](../../../src/diarization.py), +5 regels; totaal van de branch nu +51/−1 in 3 bestanden)

De tak stelt nu expliciet `"raw_speaker_intersections": []` en `"multiple_raw_speakers": False` in, met een korte uitleg in commentaar. Verder niets: winnaarslogica, velden, drempels en CRLF-regeleinden zijn ongewijzigd (volledige diff: [correction_changes_full.patch](correction_changes_full.patch)). Nieuwe hash `diarization.py`: `364196b8…` ([correction_source_hashes_after.txt](correction_source_hashes_after.txt)); `models.py` en `preprocessing.py` zijn ongewijzigd ten opzichte van de vorige oplevering.

## 3. Regressietest (klasse `RecouplingOfAnEnrichedSegment`, 7 tests, in [test_speaker_intersections.py](../../../src/tests/test_speaker_intersections.py))

Verwachtingen stonden vooraf in de docstring van de klasse.

| Stap | Verwacht | Resultaat |
|---|---|---|
| 1. Segment 0–2 verrijken met A 0–2 en B 0,5–1 | A 2,0 s + B 0,5 s, `multiple`=True, dominant A, `raw_speaker_seconds={A:2,0, B:0,5}` | geslaagd |
| 2. Opnieuw met **lege** ruwe invoer | `speaker`/`speaker_raw` None, onzeker, intersections `[]`, `multiple`=False | geslaagd |
| 3. Opnieuw met **niet-overlappende** invoer (C 5–6) | idem | geslaagd |
| 3b. Opnieuw met **ongeldige duur** (begin = eind; eind < begin), met oude intersections in het invoersegment | idem | geslaagd |
| 4. Preprocessing en JSON-rondreis (segment, `WorkshopTranscript`, `ProcessedTranscript`) | `raw_speaker_seconds={}`, `multiple`=False, geen intersections in `source_segments`, ook na herladen | geslaagd |
| 5. Geen restanten en geen mutatie | invoersegment `model_dump()` vóór = na; het invoersegment behoudt A 2,0 s en B 0,5 s; opnieuw koppelen met geldige andere beurt (C 0–2) **vervangt** de lijst (alleen C, geen A/B) | geslaagd |
| Falsificatie | een variant die de oude velden terugzet (de oorspronkelijke fout) wordt door dezelfde controle afgekeurd (lege en niet-overlappende invoer) | geslaagd |

**De test ziet de fout echt:** op een tijdelijke kopie van de huidige code waar alleen de twee nieuwe regels zijn verwijderd, falen precies de drie tests voor lege, niet-overlappende en ongeldige invoer (`[RawSpeakerIntersection(speaker_raw='A', …), …] != []`); de andere vier slagen (eerste koppeling, mutatie, vervangen, foute-variantcontrole) ([correction_tests_new_without_fix.txt](correction_tests_new_without_fix.txt)).

## 4. Testresultaten met de correctie

| Suite | Resultaat | Uitvoer |
|---|---|---|
| `Data-analysis/src/tests` | **40 OK** (17 bestaand + 16 eerdere + 7 nieuw) | [correction_tests_after_src.txt](correction_tests_after_src.txt) |
| `Experiments/classification/tests` | 51 OK | [correction_tests_after_classification.txt](correction_tests_after_classification.txt) |
| `Experiments/baseline_evaluation/tests` (harnas) | 52 OK | [correction_tests_after_baseline_eval.txt](correction_tests_after_baseline_eval.txt) |
| Voor/na op bewaarde ruwe beurten (run 1 + 2) | identiek aan de vorige oplevering: legacy-velden gelijk, dominant 19× `SPEAKER_00`, `SPEAKER_01` in segmenten 1, 4, 5, 11, 12, 15, 16 (3,898125 s), 10 turns ongewijzigd | [correction_before_after_stored_runs.json](correction_before_after_stored_runs.json) |

Regressies: **geen**. De opgeslagen uitvoerhashes van baselinerun 1 en 2 komen nog overeen met hun `run_result.json`. De correctie raakt alleen de lege-/ongeldige-tak; normale koppelingen zijn byte-gelijk aan de vorige oplevering (zelfde voor/na-JSON).

## 5. Oordeel

**Klaar om te committen** voor wat deze correctie betreft: de aangetoonde fout is opgelost, aantoonbaar door een test die zonder de correctie faalt, en alle bestaande en nieuwe tests slagen. Werkboom: `M` diarization.py, models.py, preprocessing.py; nieuw `src/tests/test_speaker_intersections.py` en de reeds eerder ongetrackte bestanden; er is niets gestaged of gecommit.
Niet behandeld (buiten de opdracht): de overige opmerkingen in de review, zoals duplicaten/overlappende records in `raw_speaker_seconds` en de duursemantiek.
