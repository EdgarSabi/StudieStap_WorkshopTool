# Modelconfiguratie en evaluatie-instellingen
## ASR (zoals vastgelegd in de baseline-JSON's, veld transcription_config; model_size=medium)
{
 "language": "nl",
 "beam_size": 5,
 "condition_on_previous_text": true,
 "repetition_penalty": 1.0,
 "no_repeat_ngram_size": 0,
 "word_timestamps": false,
 "hallucination_silence_threshold": null,
 "vad_filter": true,
 "vad_parameters": null,
 "log_prob_threshold": -1.0,
 "no_speech_threshold": 0.6,
 "compression_ratio_threshold": 2.4
}
Overig (uit TranscriptionConfig, code src/config.py): device=cpu, compute_type=int8, use_batching=False. Model: Systran/faster-whisper-medium, snapshot 08e178d48790749d25932bbc082711ddcfdfbc4f (cache NU gelezen). Bibliotheken: faster-whisper 1.2.1, ctranslate2 4.8.2, Python 3.11.5.
## WER/CER (scripts/wer_eval.py)
jiwer 4.0.0 process_words / process_characters. Normalisatie: kleine letters; tekens behalve letters/cijfers/spatie/apostrof -> spatie; '-' -> spatie; meerdere spaties samengevoegd. Referentie: kolom 'transcript' van ground_truth_<fragment>.csv in rijvolgorde, rijen met speaker_id == GEEN uitgesloten. Hypothese: segment-teksten aan elkaar.
## DER (scripts/der.py)
pyannote.metrics 4.1 DiarizationErrorRate, collar 0.0 en 0.25, skip_overlap False en True. Referentie: GT-CSV rijen (start_seconds, end_seconds, speaker_id); rijen GEEN/ONBEKEND/leeg uit referentie gelaten en hun tijd uit de UEM gehaald. UEM: 0..max(end_seconds) (testaudio1: 4.1..24.5 omdat nb_hyp alleen die slice bevat). Hypothese: elk ASR-segment uit de notebook-uitvoer met zijn speaker-label (MAIN_SPEAKER/OTHER_SPEAKER_n); optimale labelkoppeling (standaard van pyannote.metrics).
## Bekend: nb_hyp.json bevat per notebook-cel de HTML-tabel van de laatste execute_result (03: cellen 14, 21, 28; 05: cellen 2, 6, 14) geparst met html.parser; waarden zijn strings.
