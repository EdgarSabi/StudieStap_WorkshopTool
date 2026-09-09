"""
Speech-to-text via faster-whisper.

Responsible for ONLY transcription: audio in, timestamped Dutch text
out. Diarization, preprocessing, and classification are separate
stages and are deliberately not touched here.
"""
import time
from pathlib import Path

from faster_whisper import WhisperModel
try:
    from faster_whisper import BatchedInferencePipeline
    _HAS_BATCHING = True
except ImportError:
    _HAS_BATCHING = False

from config import TranscriptionConfig
from models.schema import TranscriptSegment, WorkshopTranscript

SUPPORTED_EXTENSIONS = {".mp3", ".wav", ".m4a"}


class TranscriptionEngine:
    """
    Loads the faster-whisper model once, on construction, and reuses it
    for every transcribe() call — so a batch of files doesn't reload
    the model each time.
    """

    def __init__(self, config: TranscriptionConfig):
        self.config = config
        self._model = WhisperModel(
            config.model_size,
            device=config.device,
            compute_type=config.compute_type,
        )
        self._batched_model = None
        if config.use_batching and _HAS_BATCHING:
            self._batched_model = BatchedInferencePipeline(model=self._model)

    def transcribe(self, audio_path: Path) -> WorkshopTranscript:
        if audio_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Unsupported audio format: {audio_path.suffix}. "
                f"Supported: {sorted(SUPPORTED_EXTENSIONS)}"
            )
        if not audio_path.exists():
            raise FileNotFoundError(audio_path)

        start_time = time.time()

        if self._batched_model is not None:
            segments_iter, info = self._batched_model.transcribe(
                str(audio_path),
                language=self.config.language,
                batch_size=self.config.batch_size,
            )
        else:
            segments_iter, info = self._model.transcribe(
                str(audio_path),
                language=self.config.language,
            )

        segments = [
            TranscriptSegment(start=seg.start, end=seg.end, text=seg.text.strip())
            for seg in segments_iter
        ]

        elapsed = time.time() - start_time

        return WorkshopTranscript(
            audio_file=str(audio_path),
            language=self.config.language,
            duration=info.duration,
            segments=segments,
            model_size=self.config.model_size,
            transcription_time_seconds=round(elapsed, 2),
        )