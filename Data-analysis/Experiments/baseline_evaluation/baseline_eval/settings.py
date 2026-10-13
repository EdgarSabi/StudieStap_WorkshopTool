"""Vaste keuzes van het protocol (PROTOCOL.md). Geen modelinstellingen of drempels van de pipeline."""
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
SRC = REPO / "Data-analysis" / "src"
TEST_FILES = SRC / "test-files"
GT_DIR = REPO / "Data-analysis" / "Experiments" / "diarization" / "hyperparameter_tuning"
RAW_DIR = REPO / "Data-local" / "raw"
EVAL_ROOT_DEFAULT = REPO / "Data-local" / "evaluation" / "baseline_v1"
DOCENT_REFERENCE_AUDIO = TEST_FILES / "testdocent.mp3"

# Per fragment: audio, primaire referentie, bron van spreker->rol, optionele tweede tekstreferentie.
# De primaire referentie voor audio 2 is de raster-CSV (besluit van de gebruiker).
FRAGMENTS = {
    "testaudio1_fragment": dict(audio="testaudio1_fragment.mp3", ref="ground_truth_testaudio1_fragment.csv",
                                role_source=None, manual_txt="testaudio1_manual.txt"),
    "testaudio2_fragment": dict(audio="testaudio2_fragment.mp3", ref="ground_truth_testaudio2_fragment_raster.csv",
                                role_source="ground_truth_testaudio2_fragment.csv",  # alleen speaker_id -> speaker_role
                                manual_txt="testaudio2_manual.txt"),
    "testaudio4_fragment": dict(audio="testaudio4_fragment.mp3", ref="ground_truth_testaudio4_fragment.csv",
                                role_source=None, manual_txt=None),
    "testaudio5_fragment": dict(audio="testaudio5_fragment.mp3", ref="ground_truth_testaudio5_fragment.csv",
                                role_source=None, manual_txt="testaudio5_manual.txt"),
    "testaudio7_fragment": dict(audio="testaudio7_fragment.mp3", ref="ground_truth_testaudio7_fragment.csv",
                                role_source=None, manual_txt=None),
}

# --- evaluatieparameters (vooraf vastgelegd; zie PROTOCOL.md §6-§8) ---
COLLARS_EACH_SIDE = (0.0, 0.25)   # seconden per kant van een referentiegrens (NIST/DIHARD-conventie)
UEM_MODES = ("labelled", "strict")
OVERLAP_MODES = ("keep", "exclude")
# segmentkoppeling (evaluatieontwerp, geen pipelinedrempel)
SEG_MIXED_MIN_SHARE = 0.15        # tweede referentiespreker >= 15% van het segment -> 'mixed'
SEG_MIN_KNOWN_SHARE = 0.30        # minder bekende referentiespraak dan dit -> 'no_ref_speech'
SEG_MASKED_MAX_SHARE = 0.50       # >= 50% gemaskeerd/onbekend -> 'masked'
CIRCULARITY_THRESHOLD = 0.90      # >= 90% referentierijen tekstueel gelijk aan Whisper -> 'circular'
