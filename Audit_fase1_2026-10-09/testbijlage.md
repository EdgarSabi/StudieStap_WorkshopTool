# Auditproeven — leesbare bewijsbijlage

Elke uitkomst betreft de originele functies of expliciet genoemde testdoubles. Geslaagd betekent dat de vooraf vastgelegde verwachting is bevestigd; een weerlegging kan een bug, ontwerpbeperking of methodologisch risico aantonen.

## T01 — Wordt opeenvolgende spraak onderscheiden van simultane spraak?

**Invoer:** A 0–8 s; B 8–10 s; ASR 0–10 s
**Verwacht:** overlap=False
**Geslaagd:** nee
**Conclusie:** Verwachte eigenschap weerlegd.
**Beperking:** Synthetisch; geen meting van modelkwaliteit.

**Werkelijke uitkomst:**

```json
{
  "start": 0.0,
  "end": 10.0,
  "speaker": "MAIN_SPEAKER",
  "text": "synthetische tekst",
  "avg_logprob": null,
  "no_speech_prob": null,
  "compression_ratio": null,
  "quality_flags": [],
  "speaker_raw": "A",
  "speaker_confidence": 0.8,
  "overlap": true,
  "uncertain_assignment": false
}
```

## T02 — Wordt ontbrekende diarizatie onzeker?

**Invoer:** ASR 0–10 s; geen turns
**Verwacht:** speaker=None; onzeker=True
**Geslaagd:** ja
**Conclusie:** Verwachte eigenschap bevestigd.
**Beperking:** Synthetisch; geen meting van modelkwaliteit.

**Werkelijke uitkomst:**

```json
{
  "start": 0.0,
  "end": 10.0,
  "speaker": null,
  "text": "synthetische tekst",
  "avg_logprob": null,
  "no_speech_prob": null,
  "compression_ratio": null,
  "quality_flags": [],
  "speaker_raw": null,
  "speaker_confidence": null,
  "overlap": false,
  "uncertain_assignment": true
}
```

## T03 — Wordt volledige gelijktijdige spraak onzeker?

**Invoer:** A en B beide 0–10 s
**Verwacht:** overlap=True; onzeker=True
**Geslaagd:** ja
**Conclusie:** Verwachte eigenschap bevestigd.
**Beperking:** Synthetisch; geen meting van modelkwaliteit.

**Werkelijke uitkomst:**

```json
{
  "start": 0.0,
  "end": 10.0,
  "speaker": "MAIN_SPEAKER",
  "text": "synthetische tekst",
  "avg_logprob": null,
  "no_speech_prob": null,
  "compression_ratio": null,
  "quality_flags": [],
  "speaker_raw": "A",
  "speaker_confidence": 0.5,
  "overlap": true,
  "uncertain_assignment": true
}
```

## T04 — Kan een korte tweede spreker onzichtbaar blijven?

**Invoer:** A 0–9 s; B 9–10 s; ASR 0–10 s
**Verwacht:** Tweede spreker zichtbaar als waarschuwing
**Geslaagd:** nee
**Conclusie:** Verwachte eigenschap weerlegd.
**Beperking:** Synthetisch; geen meting van modelkwaliteit.

**Werkelijke uitkomst:**

```json
{
  "start": 0.0,
  "end": 10.0,
  "speaker": "MAIN_SPEAKER",
  "text": "synthetische tekst",
  "avg_logprob": null,
  "no_speech_prob": null,
  "compression_ratio": null,
  "quality_flags": [],
  "speaker_raw": "A",
  "speaker_confidence": 0.9,
  "overlap": false,
  "uncertain_assignment": false
}
```

## T05 — Worden onlogische tijden en confidence geweigerd?

**Invoer:** start=-1; end=-2; confidence=3
**Verwacht:** ValidationError
**Geslaagd:** nee
**Conclusie:** Verwachte eigenschap weerlegd.
**Beperking:** Synthetisch; geen meting van modelkwaliteit.

**Werkelijke uitkomst:**

```json
{
  "start": -1.0,
  "end": -2.0,
  "speaker": null,
  "text": "x",
  "avg_logprob": null,
  "no_speech_prob": null,
  "compression_ratio": null,
  "quality_flags": [],
  "speaker_raw": null,
  "speaker_confidence": 3.0,
  "overlap": false,
  "uncertain_assignment": false
}
```

## T06 — Wordt verplicht tekstveld gecontroleerd?

**Invoer:** segment zonder text
**Verwacht:** ValidationError
**Geslaagd:** ja
**Conclusie:** Verwachte eigenschap bevestigd.
**Beperking:** Synthetisch; geen meting van modelkwaliteit.

**Werkelijke uitkomst:**

```json
"ValidationError"
```

## T07 — Blijven onzekere segmenten apart en bronsegmenten behouden?

**Invoer:** Twee schone, één onzeker, één schoon segment
**Verwacht:** merge-aantallen [2,1,1]; alle vier bronnen
**Geslaagd:** ja
**Conclusie:** Verwachte eigenschap bevestigd.
**Beperking:** Synthetisch; geen meting van modelkwaliteit.

**Werkelijke uitkomst:**

```json
[
  {
    "turn_id": 0,
    "speaker": "A",
    "start": 0.0,
    "end": 2.0,
    "text": "synthetische tekst synthetische tekst",
    "source_indices": [
      0,
      1
    ],
    "source_segments": [
      {
        "start": 0.0,
        "end": 1.0,
        "speaker": "A",
        "text": "synthetische tekst",
        "avg_logprob": null,
        "no_speech_prob": null,
        "compression_ratio": null,
        "quality_flags": [],
        "speaker_raw": null,
        "speaker_confidence": null,
        "overlap": false,
        "uncertain_assignment": false
      },
      {
        "start": 1.2,
        "end": 2.0,
        "speaker": "A",
        "text": "synthetische tekst",
        "avg_logprob": null,
        "no_speech_prob": null,
        "compression_ratio": null,
        "quality_flags": [],
        "speaker_raw": null,
        "speaker_confidence": null,
        "overlap": false,
        "uncertain_assignment": false
      }
    ],
    "n_segments_merged": 2,
    "overlap": false,
    "uncertain_assignment": false,
    "speaker_confidence_min": null,
    "speaker_confidence_mean": null,
    "prev_turn_id": null,
    "next_turn_id": null,
    "gap_before_seconds": null,
    "gap_after_seconds": null,
    "context_available_before": false,
    "context_available_after": false,
    "context_uncertain_before": false,
    "context_uncertain_after": false,
    "overlap_in_context": false,
    "docent_role": null,
    "docent_role_similarity": null,
    "docent_role_threshold": null,
    "docent_role_reference_audio": null,
    "docent_role_note": null
  },
  {
    "turn_id": 1,
    "speaker": "A",
    "start": 2.0,
    "end": 3.0,
    "text": "synthetische tekst",
    "source_indices": [
      2
    ],
    "source_segments": [
      {
        "start": 2.0,
        "end": 3.0,
        "speaker": "A",
        "text": "synthetische tekst",
        "avg_logprob": null,
        "no_speech_prob": null,
        "compression_ratio": null,
        "quality_flags": [],
        "speaker_raw": null,
        "speaker_confidence": null,
        "overlap": false,
        "uncertain_assignment": true
      }
    ],
    "n_segments_merged": 1,
    "overlap": false,
    "uncertain_assignment": true,
    "speaker_confidence_min": null,
    "speaker_confidence_mean": null,
    "prev_turn_id": null,
    "next_turn_id": null,
    "gap_before_seconds": null,
    "gap_after_seconds": null,
    "context_available_before": false,
    "context_available_after": false,
    "context_uncertain_before": false,
    "context_uncertain_after": false,
    "overlap_in_context": false,
    "docent_role": null,
    "docent_role_similarity": null,
    "docent_role_threshold": null,
    "docent_role_reference_audio": null,
    "docent_role_note": null
  },
  {
    "turn_id": 2,
    "speaker": "A",
    "start": 3.0,
    "end": 4.0,
    "text": "synthetische tekst",
    "source_indices": [
      3
    ],
    "source_segments": [
      {
        "start": 3.0,
        "end": 4.0,
        "speaker": "A",
        "text": "synthetische tekst",
        "avg_logprob": null,
        "no_speech_prob": null,
        "compression_ratio": null,
        "quality_flags": [],
        "speaker_raw": null,
        "speaker_confidence": null,
        "overlap": false,
        "uncertain_assignment": false
      }
    ],
    "n_segments_merged": 1,
    "overlap": false,
    "uncertain_assignment": false,
    "speaker_confidence_min": null,
    "speaker_confidence_mean": null,
    "prev_turn_id": null,
    "next_turn_id": null,
    "gap_before_seconds": null,
    "gap_after_seconds": null,
    "context_available_before": false,
    "context_available_after": false,
    "context_uncertain_before": false,
    "context_uncertain_after": false,
    "overlap_in_context": false,
    "docent_role": null,
    "docent_role_similarity": null,
    "docent_role_threshold": null,
    "docent_role_reference_audio": null,
    "docent_role_note": null
  }
]
```

## T08 — Is preprocessing bestand tegen ongeordende segmenten?

**Invoer:** A 5–6 s gevolgd door A 0–1 s
**Verwacht:** Geen turn met end<start
**Geslaagd:** nee
**Conclusie:** Verwachte eigenschap weerlegd.
**Beperking:** Synthetisch; geen meting van modelkwaliteit.

**Werkelijke uitkomst:**

```json
[
  {
    "turn_id": 0,
    "speaker": "A",
    "start": 5.0,
    "end": 1.0,
    "text": "synthetische tekst synthetische tekst",
    "source_indices": [
      0,
      1
    ],
    "source_segments": [
      {
        "start": 5.0,
        "end": 6.0,
        "speaker": "A",
        "text": "synthetische tekst",
        "avg_logprob": null,
        "no_speech_prob": null,
        "compression_ratio": null,
        "quality_flags": [],
        "speaker_raw": null,
        "speaker_confidence": null,
        "overlap": false,
        "uncertain_assignment": false
      },
      {
        "start": 0.0,
        "end": 1.0,
        "speaker": "A",
        "text": "synthetische tekst",
        "avg_logprob": null,
        "no_speech_prob": null,
        "compression_ratio": null,
        "quality_flags": [],
        "speaker_raw": null,
        "speaker_confidence": null,
        "overlap": false,
        "uncertain_assignment": false
      }
    ],
    "n_segments_merged": 2,
    "overlap": false,
    "uncertain_assignment": false,
    "speaker_confidence_min": null,
    "speaker_confidence_mean": null,
    "prev_turn_id": null,
    "next_turn_id": null,
    "gap_before_seconds": null,
    "gap_after_seconds": null,
    "context_available_before": false,
    "context_available_after": false,
    "context_uncertain_before": false,
    "context_uncertain_after": false,
    "overlap_in_context": false,
    "docent_role": null,
    "docent_role_similarity": null,
    "docent_role_threshold": null,
    "docent_role_reference_audio": null,
    "docent_role_note": null
  }
]
```

## T09 — Wordt lange stilte in context gemarkeerd?

**Invoer:** 9 s tussen twee turns
**Verwacht:** Context onzeker
**Geslaagd:** ja
**Conclusie:** Verwachte eigenschap bevestigd.
**Beperking:** Synthetisch; geen meting van modelkwaliteit.

**Werkelijke uitkomst:**

```json
[
  {
    "turn_id": 0,
    "speaker": null,
    "start": 0.0,
    "end": 1.0,
    "text": "x",
    "source_indices": [],
    "source_segments": [],
    "n_segments_merged": 0,
    "overlap": false,
    "uncertain_assignment": false,
    "speaker_confidence_min": null,
    "speaker_confidence_mean": null,
    "prev_turn_id": null,
    "next_turn_id": 1,
    "gap_before_seconds": null,
    "gap_after_seconds": 9.0,
    "context_available_before": false,
    "context_available_after": true,
    "context_uncertain_before": false,
    "context_uncertain_after": true,
    "overlap_in_context": false,
    "docent_role": null,
    "docent_role_similarity": null,
    "docent_role_threshold": null,
    "docent_role_reference_audio": null,
    "docent_role_note": null
  },
  {
    "turn_id": 1,
    "speaker": null,
    "start": 10.0,
    "end": 11.0,
    "text": "y",
    "source_indices": [],
    "source_segments": [],
    "n_segments_merged": 0,
    "overlap": false,
    "uncertain_assignment": false,
    "speaker_confidence_min": null,
    "speaker_confidence_mean": null,
    "prev_turn_id": 0,
    "next_turn_id": null,
    "gap_before_seconds": 9.0,
    "gap_after_seconds": null,
    "context_available_before": true,
    "context_available_after": false,
    "context_uncertain_before": true,
    "context_uncertain_after": false,
    "overlap_in_context": false,
    "docent_role": null,
    "docent_role_similarity": null,
    "docent_role_threshold": null,
    "docent_role_reference_audio": null,
    "docent_role_note": null
  }
]
```

## T10 — Wordt NaN-similarity als onbruikbaar behandeld?

**Invoer:** Fake recognizer retourneert NaN
**Verwacht:** ONZEKER
**Geslaagd:** nee
**Conclusie:** Verwachte eigenschap weerlegd.
**Beperking:** Synthetisch; geen meting van modelkwaliteit.

**Werkelijke uitkomst:**

```json
{
  "turn_id": 0,
  "speaker": "OTHER_SPEAKER_1",
  "start": 0.0,
  "end": 2.0,
  "text": "x",
  "source_indices": [],
  "source_segments": [],
  "n_segments_merged": 0,
  "overlap": false,
  "uncertain_assignment": false,
  "speaker_confidence_min": null,
  "speaker_confidence_mean": null,
  "prev_turn_id": null,
  "next_turn_id": null,
  "gap_before_seconds": null,
  "gap_after_seconds": null,
  "context_available_before": false,
  "context_available_after": false,
  "context_uncertain_before": false,
  "context_uncertain_after": false,
  "overlap_in_context": false,
  "docent_role": "OTHER",
  "docent_role_similarity": "nan",
  "docent_role_threshold": 0.35,
  "docent_role_reference_audio": "synthetic.wav",
  "docent_role_note": null
}
```

## T11 — Is een nulvector bewijs voor OTHER?

**Invoer:** Cosine van twee nulvectoren
**Verwacht:** ONZEKER bij onbruikbare embedding
**Geslaagd:** nee
**Conclusie:** Verwachte eigenschap weerlegd.
**Beperking:** Synthetisch; geen meting van modelkwaliteit.

**Werkelijke uitkomst:**

```json
{
  "similarity": 0.0,
  "role": "OTHER"
}
```

## T12 — Wordt werkelijke cliplengte gecontroleerd?

**Invoer:** Turn 0–2 s; audio slechts 0.25 s; similarity 0.8
**Verwacht:** ONZEKER zonder embedding
**Geslaagd:** nee
**Conclusie:** Verwachte eigenschap weerlegd.
**Beperking:** Synthetisch; geen meting van modelkwaliteit.

**Werkelijke uitkomst:**

```json
{
  "role": "DOCENT",
  "samples": [
    4000
  ]
}
```

## T13 — Is docentrol onafhankelijk van MAIN_SPEAKER?

**Invoer:** OTHER_SPEAKER_1; similarity 0.8
**Verwacht:** DOCENT
**Geslaagd:** ja
**Conclusie:** Verwachte eigenschap bevestigd.
**Beperking:** Synthetisch; geen meting van modelkwaliteit.

**Werkelijke uitkomst:**

```json
{
  "turn_id": 0,
  "speaker": "OTHER_SPEAKER_1",
  "start": 0.0,
  "end": 2.0,
  "text": "x",
  "source_indices": [],
  "source_segments": [],
  "n_segments_merged": 0,
  "overlap": false,
  "uncertain_assignment": false,
  "speaker_confidence_min": null,
  "speaker_confidence_mean": null,
  "prev_turn_id": null,
  "next_turn_id": null,
  "gap_before_seconds": null,
  "gap_after_seconds": null,
  "context_available_before": false,
  "context_available_after": false,
  "context_uncertain_before": false,
  "context_uncertain_after": false,
  "overlap_in_context": false,
  "docent_role": "DOCENT",
  "docent_role_similarity": 0.8,
  "docent_role_threshold": 0.35,
  "docent_role_reference_audio": "synthetic.wav",
  "docent_role_note": null
}
```

## T14 — Blijven meerdere leerlingidentiteiten afzonderlijk?

**Invoer:** A/B/C; A spreekt korter dan B
**Verwacht:** Drie afzonderlijke friendly labels
**Geslaagd:** ja
**Conclusie:** Verwachte eigenschap bevestigd.
**Beperking:** Synthetisch; geen meting van modelkwaliteit.

**Werkelijke uitkomst:**

```json
{
  "map": {
    "B": "MAIN_SPEAKER",
    "A": "OTHER_SPEAKER_1",
    "C": "OTHER_SPEAKER_2"
  },
  "inventory": [
    {
      "raw": "B",
      "label": "MAIN_SPEAKER",
      "talk_seconds": 3.0,
      "share": 0.6
    },
    {
      "raw": "A",
      "label": "OTHER_SPEAKER_1",
      "talk_seconds": 1.0,
      "share": 0.2
    },
    {
      "raw": "C",
      "label": "OTHER_SPEAKER_2",
      "talk_seconds": 1.0,
      "share": 0.2
    }
  ],
  "main_speaker_uncertain": false
}
```

## T15 — Hebben verschillende bronnen verschillende cachepaden?

**Invoer:** /a/clip.mp3 en /b/clip.wav
**Verwacht:** Verschillende outputpaden
**Geslaagd:** nee
**Conclusie:** Verwachte eigenschap weerlegd.
**Beperking:** Synthetisch; geen meting van modelkwaliteit.

**Werkelijke uitkomst:**

```json
"C:\\Users\\School\\Projects\\StudieStap_WorkshopTool\\Audit_fase1_2026-10-09\\clip.json | C:\\Users\\School\\Projects\\StudieStap_WorkshopTool\\Audit_fase1_2026-10-09\\clip.json"
```

## T16 — Komen batchinginstellingen overeen met opgeslagen config?

**Invoer:** Fake Whisper; beam=2; VAD=False; words=True
**Verwacht:** Alle ingestelde parameters doorgestuurd
**Geslaagd:** nee
**Conclusie:** Verwachte eigenschap weerlegd.
**Beperking:** Modelaanroepen vervangen door testdoubles; uitsluitend wrapperlogica getest.

**Werkelijke uitkomst:**

```json
{
  "actual_call": [
    {
      "language": "nl",
      "batch_size": 8
    }
  ],
  "recorded": {
    "language": "nl",
    "beam_size": 2,
    "condition_on_previous_text": true,
    "repetition_penalty": 1.0,
    "no_repeat_ngram_size": 0,
    "word_timestamps": true,
    "hallucination_silence_threshold": null,
    "vad_filter": false,
    "vad_parameters": null,
    "log_prob_threshold": -1.0,
    "no_speech_threshold": 0.6,
    "compression_ratio_threshold": 2.4
  },
  "segment": {
    "start": 0.0,
    "end": 1.0,
    "speaker": null,
    "text": "x",
    "avg_logprob": -0.1,
    "no_speech_prob": 0.1,
    "compression_ratio": 1.0,
    "quality_flags": [],
    "speaker_raw": null,
    "speaker_confidence": null,
    "overlap": false,
    "uncertain_assignment": false
  }
}
```

## T17 — Wordt herhalende tekst gemarkeerd?

**Invoer:** de de de de de de
**Verwacht:** possible_repetition_hallucination
**Geslaagd:** ja
**Conclusie:** Verwachte eigenschap bevestigd.
**Beperking:** Synthetisch; geen meting van modelkwaliteit.

**Werkelijke uitkomst:**

```json
[
  "possible_repetition_hallucination"
]
```

## T18 — Kan WAV met 24-bit samples via conversie worden verwerkt?

**Invoer:** Synthetisch geldige 24-bit PCM WAV
**Verwacht:** Conversie of succesvolle verwerking
**Geslaagd:** nee
**Conclusie:** Verwachte eigenschap weerlegd.
**Beperking:** Synthetisch; geen meting van modelkwaliteit.

**Werkelijke uitkomst:**

```json
{
  "returned_unchanged": true,
  "error": "synthetic_24.wav has 24-bit samples; to_wav() should produce 16-bit PCM."
}
```

## T19 — Wordt onverwachte sample rate correct doorgegeven door WAV-loader?

**Invoer:** 48 kHz; stereo; één seconde
**Verwacht:** sample_rate=48000; shape [2,48000]
**Geslaagd:** ja
**Conclusie:** Verwachte eigenschap bevestigd.
**Beperking:** Geen test van resampling binnen pyannote.

**Werkelijke uitkomst:**

```json
{
  "sr": 48000,
  "shape": [
    2,
    48000
  ]
}
```

## T20 — Wordt een gedeeltelijke WAV gedetecteerd?

**Invoer:** Header zegt 16000 frames; bestand afgekapt tot 100 bytes
**Verwacht:** Expliciete fout of incompleet-status
**Geslaagd:** nee
**Conclusie:** Verwachte eigenschap weerlegd.
**Beperking:** Synthetisch; geen meting van modelkwaliteit.

**Werkelijke uitkomst:**

```json
{
  "samples": 28,
  "header_samples": 16000
}
```

## T21 — Bestraft de bestaande score false alarms en extra speakers?

**Invoer:** GT A 0–1 s; hyp X 0–100 s plus Y 0–1 s
**Verwacht:** Score lager dan 100%
**Geslaagd:** nee
**Conclusie:** Verwachte eigenschap weerlegd.
**Beperking:** Synthetisch; geen meting van modelkwaliteit.

**Werkelijke uitkomst:**

```json
{
  "gt_speakers": 1,
  "pyannote_speakers_found": 2,
  "overall_correct_pct": 100.0,
  "per_gt_speaker": {
    "A": {
      "seconds": 1.0,
      "matched_pyannote_speaker": "X",
      "covered_pct": 100.0
    }
  }
}
```

## T22 — Kan lege referentie veilig worden gescoord?

**Invoer:** Geen GT; geen hypothese
**Verwacht:** Geen score; expliciete onbruikbare referentie
**Geslaagd:** nee
**Conclusie:** Verwachte eigenschap weerlegd.
**Beperking:** Synthetisch; geen meting van modelkwaliteit.

**Werkelijke uitkomst:**

```json
"ZeroDivisionError: division by zero"
```

## T23 — Dwingt status OK een bruikbaar resultaat af?

**Invoer:** OK; detected=None; evidence=None
**Verwacht:** ValidationError
**Geslaagd:** nee
**Conclusie:** Verwachte eigenschap weerlegd.
**Beperking:** Synthetisch; geen meting van modelkwaliteit.

**Werkelijke uitkomst:**

```json
{
  "fragment_id": "x",
  "center_turn_id": 0,
  "context_turn_ids": [
    0
  ],
  "indicator_id": "placeholder",
  "detected": null,
  "evidence": null,
  "status": "OK",
  "model_name": "mock",
  "model_version": "0",
  "prompt_version": "0"
}
```

## T24 — Weigert schema niet-eindige tijdstempels?

**Invoer:** start NaN; end Infinity
**Verwacht:** ValidationError
**Geslaagd:** nee
**Conclusie:** Verwachte eigenschap weerlegd.
**Beperking:** Synthetisch; geen meting van modelkwaliteit.

**Werkelijke uitkomst:**

```json
{
  "start_is_nan": true,
  "json": "{\"start\":null,\"end\":null,\"speaker\":null,\"text\":\"x\",\"avg_logprob\":null,\"no_speech_prob\":null,\"compression_ratio\":null,\"quality_flags\":[],\"speaker_raw\":null,\"speaker_confidence\":null,\"overlap\":false,\"uncertain_assignment\":false}"
}
```

## T25 — Blijft een onbekend extra bronveld behouden?

**Invoer:** TranscriptSegment met extra_marker=preserve
**Verwacht:** Extra bronveld in JSON
**Geslaagd:** nee
**Conclusie:** Verwachte eigenschap weerlegd.
**Beperking:** Synthetisch; geen meting van modelkwaliteit.

**Werkelijke uitkomst:**

```json
{
  "start": 0.0,
  "end": 1.0,
  "speaker": null,
  "text": "x",
  "avg_logprob": null,
  "no_speech_prob": null,
  "compression_ratio": null,
  "quality_flags": [],
  "speaker_raw": null,
  "speaker_confidence": null,
  "overlap": false,
  "uncertain_assignment": false
}
```

## T26 — Blijven ontbrekende kwaliteitsvelden onbekend?

**Invoer:** Segment met alleen start,end,text,speaker
**Verwacht:** Niet automatisch als schoon behandeld
**Geslaagd:** nee
**Conclusie:** Verwachte eigenschap weerlegd.
**Beperking:** Synthetisch; geen meting van modelkwaliteit.

**Werkelijke uitkomst:**

```json
{
  "start": 0.0,
  "end": 1.0,
  "speaker": "A",
  "text": "x",
  "avg_logprob": null,
  "no_speech_prob": null,
  "compression_ratio": null,
  "quality_flags": [],
  "speaker_raw": null,
  "speaker_confidence": null,
  "overlap": false,
  "uncertain_assignment": false
}
```

## T27 — Worden niet-spraak en onbekende identiteit apart gehouden in scoring?

**Invoer:** Bestaande CSV 1 en 5
**Verwacht:** GEEN/ONBEKEND geen gewone sprekeridentiteit
**Geslaagd:** nee
**Conclusie:** Verwachte eigenschap weerlegd.
**Beperking:** CSV gelezen; geen verificatie van annotaties tegen audio.

**Werkelijke uitkomst:**

```json
{
  "audio1": [
    "GEEN",
    "SPREKER_A",
    "SPREKER_B"
  ],
  "audio5": [
    "ONBEKEND",
    "SPREKER_A",
    "SPREKER_B",
    "SPREKER_C"
  ]
}
```

## T28 — Wordt een corrupte transcriptcache afgewezen?

**Invoer:** Bestaand cachebestand met alleen {
**Verwacht:** Cache niet bruikbaar
**Geslaagd:** nee
**Conclusie:** Verwachte eigenschap weerlegd.
**Beperking:** Synthetisch; geen meting van modelkwaliteit.

**Werkelijke uitkomst:**

```json
{
  "cache_found": true,
  "contents": "{"
}
```

## T29 — Blijven ongelabelde tekstregels van de bestaande handmatige referentie behouden?

**Invoer:** testaudio1_manual.txt via Notebook 03 cel 5
**Verwacht:** Alle niet-lege gesproken regels behouden
**Geslaagd:** nee
**Conclusie:** Verwachte eigenschap weerlegd.
**Beperking:** Geen controle van de woorden tegen ontbrekende audio.

**Werkelijke uitkomst:**

```json
{
  "nonempty_lines": 9,
  "loaded_rows": 5,
  "omitted_lines": 4
}
```

## T30 — Is agreement vrij van de aanname MAIN=docent?

**Invoer:** MAIN is leerling; recognition OTHER
**Verwacht:** Geen conflict over correct herkende leerling
**Geslaagd:** nee
**Conclusie:** Verwachte eigenschap weerlegd.
**Beperking:** Synthetisch; geen meting van modelkwaliteit.

**Werkelijke uitkomst:**

```json
{
  "scenario": "Leerling spreekt het meest; recognizer correct OTHER",
  "agreement": [
    "conflict_diar_main_sim_low",
    true
  ]
}
```

## T31 — Volgt refinement de gedocumenteerde overlapratio?

**Invoer:** Nieuw segment 0–10 s; baseline 0–1 s
**Verwacht:** A: volledige overlap van kortste segment
**Geslaagd:** nee
**Conclusie:** Verwachte eigenschap weerlegd.
**Beperking:** Originele functie uit AST uitgevoerd; rest van experimentele module niet uitgevoerd.

**Werkelijke uitkomst:**

```json
{
  "result": null,
  "overlap_over_shorter": 1.0,
  "overlap_over_new_segment": 0.1
}
```

## T32 — Blokkeren slechte ASR-signalen een stellige docentrol?

**Invoer:** Schone diarizatie; twee ASR-quality_flags; fake similarity 0.8
**Verwacht:** Rol onzeker of expliciet kwaliteitsvoorbehoud
**Geslaagd:** nee
**Conclusie:** Verwachte eigenschap weerlegd.
**Beperking:** Bewezen gedrag; ontbreken blokkade is een methodologisch risico, geen bewezen verkeerde stemherkenning.

**Werkelijke uitkomst:**

```json
{
  "turn_id": 0,
  "speaker": "A",
  "start": 0.0,
  "end": 2.0,
  "text": "x",
  "source_indices": [],
  "source_segments": [
    {
      "start": 0.0,
      "end": 2.0,
      "speaker": null,
      "text": "x",
      "avg_logprob": null,
      "no_speech_prob": null,
      "compression_ratio": null,
      "quality_flags": [
        "high_no_speech_prob",
        "low_avg_logprob"
      ],
      "speaker_raw": null,
      "speaker_confidence": null,
      "overlap": false,
      "uncertain_assignment": false
    }
  ],
  "n_segments_merged": 0,
  "overlap": false,
  "uncertain_assignment": false,
  "speaker_confidence_min": null,
  "speaker_confidence_mean": null,
  "prev_turn_id": null,
  "next_turn_id": null,
  "gap_before_seconds": null,
  "gap_after_seconds": null,
  "context_available_before": false,
  "context_available_after": false,
  "context_uncertain_before": false,
  "context_uncertain_after": false,
  "overlap_in_context": false,
  "docent_role": "DOCENT",
  "docent_role_similarity": 0.8,
  "docent_role_threshold": 0.35,
  "docent_role_reference_audio": "synthetic.wav",
  "docent_role_note": null
}
```
