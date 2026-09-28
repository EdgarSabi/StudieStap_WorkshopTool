"""
Prompt building, kept separate from the classifier call (STAP 4) and from
context selection (STAP 3). This is a PLACEHOLDER template — no didactic
indicator definitions live here (those aren't operationalized yet, per
Fase 5A's scope). Swapping in real indicator definitions later only means
changing this function/version, not the classifier interface or the
pipeline around it.
"""
from context.selector import ContextWindow

# v1: added docent_role per turn (Phase 4 integration) — bumped because the
# rendered prompt text itself changed, per STAP 6 reproducibility (a stored
# prompt_version must identify which template actually produced a prompt).
PROMPT_VERSION = "placeholder-v1"


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
        # docent_role is a separate, independently-computed judgement (Phase 4
        # voice recognition) — NEVER inferred from `speaker` here either.
        # None means "not evaluated", shown as-is rather than guessed.
        docent_role = t.docent_role or "ONBEKEND"
        lines.append(f"  [{marker}] turn {t.turn_id} ({speaker}, docent_role={docent_role}): {t.text}")
    lines.append("")
    lines.append(
        "This is a placeholder prompt for pipeline testing only — it does not "
        "encode a real didactic indicator definition or scoring rule."
    )
    return "\n".join(lines)
