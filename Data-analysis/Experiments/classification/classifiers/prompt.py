"""
Prompt building, kept separate from the classifier call (STAP 4) and from
context selection (STAP 3). This is a PLACEHOLDER template — no didactic
indicator definitions live here (those aren't operationalized yet, per
Fase 5A's scope). Swapping in real indicator definitions later only means
changing this function/version, not the classifier interface or the
pipeline around it.
"""
from context.selector import ContextWindow

PROMPT_VERSION = "placeholder-v0"


def build_prompt(window: ContextWindow, indicator_id: str) -> str:
    lines = [
        f"INDICATOR: {indicator_id}  (placeholder — not yet operationalized)",
        f"CONTEXT MODE: {window.mode}",
        "",
        "CONTEXT (chronological order, [*] marks the turn to judge):",
    ]
    for t in window.turns:
        marker = "*" if t.turn_id == window.center_turn_id else " "
        speaker = t.speaker or "UNKNOWN_SPEAKER"
        lines.append(f"  [{marker}] turn {t.turn_id} ({speaker}): {t.text}")
    lines.append("")
    lines.append(
        "This is a placeholder prompt for pipeline testing only — it does not "
        "encode a real didactic indicator definition or scoring rule."
    )
    return "\n".join(lines)
