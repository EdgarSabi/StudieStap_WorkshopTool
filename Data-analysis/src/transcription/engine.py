"""
Speech-to-text via faster-whisper, with configurable decoding parameters
and post-hoc quality flagging for benchmarking. The raw model output is
never dropped or rewritten here — flags are metadata, not filtering.
"""
import re
import time
from collections import Counter
from pathlib import Path

from faster_whisper import WhisperModel

from config import TranscriptionConfig
from models.schema import TranscriptSegment, WorkshopTranscript

SUPPORTED_EXTENSIONS = {".mp3", ".wav", ".m4a"}


def _detect_quality_flags(text, avg_logprob, no_speech_prob, compression_ratio, config: TranscriptionConfig) -> list[str]:
    """
    Heuristic flagging to support manual review — thresholds are configurable
    and NOT research conclusions about what counts as a "bad" segment.
    """
    flags = []

    if avg_logprob is not None and avg_logprob < config.flag_avg_logprob_below:
        flags.append("low_avg_logprob")
    if no_speech_prob is not None and no_speech_prob > config.flag_no_speech_prob_above:
        flags.append("high_no_speech_prob")
    if compression_ratio is not None and compression_ratio > config.flag_compression_ratio_above:
        flags.append("high_compression_ratio")

    words = text.strip().split()
    if len(words) >= config.flag_repetition_min_words:
        word, count = Counter(w.lower() for w in words).most_common(1)[0]
        if count / len(words) >= config.flag_repetition_word_ratio:
            flags.append("possible_repetition_hallucination")

    # catches short repeated phrases, e.g. "de de de de de de"
    if re.search(r"\b(\w+(?:\s+\w+){0,2})\b(?:\s+\1\b){3,}", text, flags=re.IGNORECASE):
        if "possible_repetition_hallucination" not in flags:
            flags.append("possible_repetition_hallucination")

    return flags


class TranscriptionEngine:
    def __init__(self, config: TranscriptionConfig):
        self.config = config
        self._model = WhisperModel(
            config.model_size,
            device=config.device,
            compute_type=config.compute_type,
        )
        self._batched_model = None
        if config.use_batching:
            from faster_whisper import BatchedInferencePipeline
            self._batched_model = BatchedInferencePipeline(model=self._model)

    def transcribe(self, audio_path: Path) -> WorkshopTranscript:
        if audio_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported audio format: {audio_path.suffix}")
        if not audio_path.exists():
            raise FileNotFoundError(audio_path)

        transcribe_kwargs = dict(
            language=self.config.language,
            beam_size=self.config.beam_size,
            condition_on_previous_text=self.config.condition_on_previous_text,
            repetition_penalty=self.config.repetition_penalty,
            no_repeat_ngram_size=self.config.no_repeat_ngram_size,
            word_timestamps=self.config.word_timestamps,
            hallucination_silence_threshold=self.config.hallucination_silence_threshold,
            vad_filter=self.config.vad_filter,
            vad_parameters=self.config.vad_parameters,
            log_prob_threshold=self.config.log_prob_threshold,
            no_speech_threshold=self.config.no_speech_threshold,
            compression_ratio_threshold=self.config.compression_ratio_threshold,
        )

        start_time = time.time()

        if self._batched_model is not None:
            segments_iter, info = self._batched_model.transcribe(
                str(audio_path), language=self.config.language, batch_size=self.config.batch_size,
            )
        else:
            segments_iter, info = self._model.transcribe(str(audio_path), **transcribe_kwargs)

        segments = []
        for seg in segments_iter:
            flags = _detect_quality_flags(
                seg.text, seg.avg_logprob, seg.no_speech_prob, seg.compression_ratio, self.config
            )
            segments.append(TranscriptSegment(
                start=seg.start, end=seg.end, text=seg.text.strip(),
                avg_logprob=seg.avg_logprob,
                no_speech_prob=seg.no_speech_prob,
                compression_ratio=seg.compression_ratio,
                quality_flags=flags,
            ))

        elapsed = time.time() - start_time

        return WorkshopTranscript(
            audio_file=str(audio_path),
            language=self.config.language,
            duration=info.duration,
            segments=segments,
            model_size=self.config.model_size,
            transcription_time_seconds=round(elapsed, 2),
            transcription_config=transcribe_kwargs,
        )