# Uitgevoerde commando's — RECONSTRUCTIE uit het gesprek, GEEN origineel logbestand
Er is geen shell-history of logbestand van de commando's bewaard behalve asr_log.txt (stdout van stap 2) en de taak-outputs in tasks/.
Volgorde zoals uitgevoerd (scripts in scripts/):
1. python extract_nb.py <scratchpad>      -> nb_hyp.json  (EERSTE run schreef met cp1252; daarna met sed gecorrigeerd naar utf-8 en OPNIEUW gedraaid. De eerste versie is overschreven en bestaat niet meer; dit is de tweede.)
2. python run_asr_baseline.py <scratchpad>/asr testaudio2_fragment testaudio1_fragment testaudio5_fragment testaudio7_fragment testaudio4_fragment   (nohup, stdout -> asr_log.txt)
3. python der.py <scratchpad>            (collar 0/0.25, skip_overlap False/True; uitvoer alleen in het gesprek, niet in bestand)
4. python wer_eval.py <scratchpad>       -> wer_results.json (laatste run, met alle 5 fragmenten; eerdere runs bevatten 3-4 fragmenten en zijn overschreven)
5. python run_synth.py <scratchpad>      -> synth_results.json
6. python edge_tests.py <scratchpad>     -> edge_results.json
Let op: der.py is tijdens de audit eenmaal aangepast (uem-regels verwijderd na een foutieve eerste versie); scripts/der.py is de uiteindelijke versie. De uitvoer van der.py is niet als bestand bewaard: de DER-getallen staan alleen in het gesprek en in auditrapport_fase1.md (T4).
