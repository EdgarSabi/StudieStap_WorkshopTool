"""
Map raw diarization speaker ids (SPEAKER_00, SPEAKER_01, ...) onto the labels
this project actually cares about for the MVP:

    MAIN_SPEAKER      - the speaker with the most total talk time in the fragment
    OTHER_SPEAKER_1   - next most talk time
    OTHER_SPEAKER_2   - ...

This is a heuristic for classroom recordings where the teacher / StudieStapper
does most of the talking. It is NOT speaker identification and makes no claim
about who any OTHER_SPEAKER is. The choice is revisited in later phases.
"""
from .base import DiarizationResult

MAIN_SPEAKER = "MAIN_SPEAKER"


def build_label_map(result: DiarizationResult, *, main_speaker_min_share: float = 0.0) -> dict:
    """Return {raw_label: friendly_label} plus a small inventory for the report.

    Structure:
      {
        "map": {"SPEAKER_00": "MAIN_SPEAKER", "SPEAKER_01": "OTHER_SPEAKER_1", ...},
        "inventory": [
          {"raw": "SPEAKER_00", "label": "MAIN_SPEAKER", "talk_seconds": 61.2, "share": 0.74},
          ...
        ],
        "main_speaker_uncertain": False,
      }
    """
    talk = result.talk_time()
    total = sum(talk.values())
    ranked = sorted(talk.items(), key=lambda kv: kv[1], reverse=True)

    label_map: dict[str, str] = {}
    inventory = []
    for i, (raw, seconds) in enumerate(ranked):
        friendly = MAIN_SPEAKER if i == 0 else f"OTHER_SPEAKER_{i}"
        label_map[raw] = friendly
        inventory.append(
            {
                "raw": raw,
                "label": friendly,
                "talk_seconds": round(seconds, 2),
                "share": round(seconds / total, 4) if total else 0.0,
            }
        )

    main_share = ranked[0][1] / total if (ranked and total) else 0.0
    return {
        "map": label_map,
        "inventory": inventory,
        "main_speaker_uncertain": main_share < main_speaker_min_share,
    }
