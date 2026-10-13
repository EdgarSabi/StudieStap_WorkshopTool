"""Instellingen laden uit config.yaml en het geheim (HF_TOKEN) uit .env.

Standaardwaarden staan hieronder in de dataclasses. config.yaml overschrijft ze.
Onbekende sleutels in config.yaml geven een foutmelding, zodat een typfout niet
stilletjes genegeerd wordt.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Optional

import yaml

from .models import StudieStapError, to_dict


@dataclass
class TranscriptionSettings:
    model_size: str = "medium"
    language: str = "nl"
    device: str = "cpu"
    compute_type: str = "int8"
    beam_size: int = 5
    condition_on_previous_text: bool = True
    vad_filter: bool = True
    word_timestamps: bool = False


@dataclass
class DiarizationSettings:
    backend: str = "pyannote"
    model: str = "pyannote/speaker-diarization-3.1"
    device: str = "cpu"
    min_speakers: Optional[int] = None
    max_speakers: Optional[int] = None


@dataclass
class AlignmentSettings:
    enabled: bool = True
    device: str = "cpu"


@dataclass
class SpeakerSettings:
    min_single_speaker_coverage: float = 0.60


@dataclass
class TeacherSettings:
    embedding_model: str = "pyannote/wespeaker-voxceleb-resnet34-LM"
    device: str = "cpu"
    similarity_threshold: float = 0.35
    min_clip_seconds: float = 1.0


@dataclass
class VoiceConsistencySettings:
    enabled: bool = False   # optionele extra diagnostiek; model/apparaat komen uit teacher_recognition


@dataclass
class QualitySettings:
    whisper_avg_logprob_below: float = -1.0
    whisper_no_speech_prob_above: float = 0.6
    whisper_compression_ratio_above: float = 2.4


@dataclass
class HuggingFaceSettings:
    offline: bool = False


@dataclass
class OutputSettings:
    directory: str = "output"
    keep_audio: bool = False


@dataclass
class Settings:
    transcription: TranscriptionSettings = field(default_factory=TranscriptionSettings)
    diarization: DiarizationSettings = field(default_factory=DiarizationSettings)
    alignment: AlignmentSettings = field(default_factory=AlignmentSettings)
    speakers: SpeakerSettings = field(default_factory=SpeakerSettings)
    teacher_recognition: TeacherSettings = field(default_factory=TeacherSettings)
    voice_consistency: VoiceConsistencySettings = field(default_factory=VoiceConsistencySettings)
    quality: QualitySettings = field(default_factory=QualitySettings)
    huggingface: HuggingFaceSettings = field(default_factory=HuggingFaceSettings)
    output: OutputSettings = field(default_factory=OutputSettings)

    def to_dict(self) -> dict:
        """Voor provenance. Bevat bewust geen token."""
        return to_dict(self)


def _fill(section_obj, values: dict, section_name: str) -> None:
    allowed = {f.name for f in fields(section_obj)}
    for key, value in values.items():
        if key not in allowed:
            raise StudieStapError(
                f"Onbekende instelling '{section_name}.{key}' in config.yaml.",
                hint=f"Toegestaan in '{section_name}': {', '.join(sorted(allowed))}.",
            )
        setattr(section_obj, key, value)


def load_settings(config_path: Optional[Path] = None) -> Settings:
    """Laad config.yaml. Zonder pad: ./config.yaml als die bestaat, anders standaardwaarden."""
    settings = Settings()
    if config_path is None:
        candidate = Path("config.yaml")
        config_path = candidate if candidate.exists() else None
    elif not Path(config_path).exists():
        raise StudieStapError(f"Configuratiebestand niet gevonden: {config_path}",
                              hint="Controleer het pad bij --config.")
    if config_path is None:
        return settings

    try:
        raw = yaml.safe_load(Path(config_path).read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        raise StudieStapError(f"config.yaml is geen geldige YAML: {e}",
                              hint="Let op inspringing met spaties en dubbele punten.") from e
    if not isinstance(raw, dict):
        raise StudieStapError("config.yaml moet bestaan uit secties met instellingen.")

    for section, values in raw.items():
        if not hasattr(settings, section):
            raise StudieStapError(
                f"Onbekende sectie '{section}' in config.yaml.",
                hint=f"Toegestaan: {', '.join(f.name for f in fields(settings))}.",
            )
        if not isinstance(values, dict):
            raise StudieStapError(f"Sectie '{section}' in config.yaml moet instellingen bevatten.")
        _fill(getattr(settings, section), values, section)
    return settings


def load_environment(env_path: Optional[Path] = None) -> None:
    """Laad .env (als die bestaat) in de omgevingsvariabelen. Overschrijft niets wat al is gezet."""
    from dotenv import load_dotenv
    load_dotenv(env_path or Path(".env"), override=False)


def get_hf_token() -> Optional[str]:
    """Het Hugging Face-token, of None. Wordt nooit gelogd of in uitvoer gezet."""
    return os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN")


def apply_offline_mode(settings: Settings) -> None:
    """Met huggingface.offline: true gebruiken we alleen lokaal gecachete modellen."""
    if settings.huggingface.offline:
        os.environ["HF_HUB_OFFLINE"] = "1"
