"""Kwaliteitssignalen: verzamel wat al bekend is, zonder het te oordelen.

Twee soorten uitspraken worden NIET door elkaar gehaald:
  * "waargenomen signaal"   - dit is gezien (bijv. twee sprekers in een segment)
  * "bewezen onbetrouwbaar" - dat weten we hier NIET; daarvoor is onderzoek nodig
Elk `Signal` heeft daarom kind="observed".

Segmentstatus (voorlopig, zonder gekalibreerde drempels):
  NOT_ASSESSABLE   er is geen tekst in het segment
  REVIEW_REQUIRED  er is minstens een waargenomen signaal -> kijk er zelf naar
  ASSESSABLE       geen signalen waargenomen. Dit is GEEN bewijs van betrouwbaarheid.
De echte regels komen uit onderzoeksfases 3 en 4. Hier staat alleen de plek ervoor.
"""
from __future__ import annotations

from typing import Optional

from ..models import (QualityReport, ReviewStatus, SegmentQuality, SegmentSpeakers, SegmentVoiceCheck, Signal,
                      SpeakerRole, StepStatus, Transcript, WordAlignment)
from ..settings import QualitySettings

NOTE = ("Signalen zijn waarnemingen, geen bewijs van onbetrouwbaarheid. ASSESSABLE betekent alleen: "
        "geen signalen waargenomen. Definitieve kwaliteitsregels volgen uit onderzoeksfases 3 en 4.")


def build_quality_report(
    transcript: Transcript,
    speakers: Optional[list[SegmentSpeakers]],
    alignment: Optional[WordAlignment],
    roles: Optional[list[SpeakerRole]],
    settings: QualitySettings,
    voice_checks: Optional[list[SegmentVoiceCheck]] = None,
) -> QualityReport:
    report = QualityReport(note=NOTE)
    g = report.global_signals

    if not transcript.segments:
        g.append(Signal("NO_SEGMENTS", "De transcriptie bevat geen segmenten."))
    if speakers is None:
        g.append(Signal("DIARIZATION_MISSING", "Geen sprekerinformatie beschikbaar."))
    if alignment is None or alignment.status != StepStatus.SUCCEEDED:
        state = alignment.status.value if alignment else "not_run"
        g.append(Signal("WORD_ALIGNMENT_" + state.upper(),
                        f"Woorduitlijning: {state}. Geen (volledige) woordnauwkeurige claims mogelijk."))
    role_by_speaker = {r.speaker: r for r in (roles or [])}
    if roles is not None and roles and all(r.identity_status == "NO_REFERENCE" for r in roles):
        g.append(Signal("NO_TEACHER_REFERENCE", "Geen referentieopname: docentidentiteit onbekend."))
    if sum(r.identity_status == "MATCH" for r in role_by_speaker.values()) > 1:
        g.append(Signal("MULTIPLE_TEACHER_MATCHES",
                        "Meerdere sprekers lijken op de referentiedocent (diarizatie kan een persoon gesplitst hebben)."))

    speakers_by_id = {s.segment_id: s for s in (speakers or [])}
    voice_by_id = {v.segment_id: v for v in (voice_checks or [])}
    for seg in transcript.segments:
        sigs: list[Signal] = []

        def add(code: str, detail: str):
            sigs.append(Signal(code, detail, segment_id=seg.id))

        if not seg.text.strip():
            add("EMPTY_TEXT", "Segment bevat geen tekst.")
        if seg.avg_logprob is not None and seg.avg_logprob < settings.whisper_avg_logprob_below:
            add("ASR_LOW_AVG_LOGPROB", f"avg_logprob {seg.avg_logprob:.2f} < {settings.whisper_avg_logprob_below}")
        if seg.no_speech_prob is not None and seg.no_speech_prob > settings.whisper_no_speech_prob_above:
            add("ASR_HIGH_NO_SPEECH_PROB",
                f"no_speech_prob {seg.no_speech_prob:.2f} > {settings.whisper_no_speech_prob_above}")
        if seg.compression_ratio is not None and seg.compression_ratio > settings.whisper_compression_ratio_above:
            add("ASR_HIGH_COMPRESSION_RATIO",
                f"compression_ratio {seg.compression_ratio:.2f} > {settings.whisper_compression_ratio_above}")

        sp = speakers_by_id.get(seg.id)
        if sp is not None:
            if sp.attribution == "NONE":
                add("SPEAKER_NONE", "Geen enkel sprekerinterval overlapt dit segment.")
            elif sp.attribution == "MIXED":
                add("SPEAKER_MIXED", f"Meerdere ruwe sprekers in dit segment: {sorted(sp.seconds_per_speaker)}.")
            elif sp.attribution == "PARTIAL":
                add("SPEAKER_PARTIAL", "De enige spreker dekt maar een deel van het segment.")
            if sp.simultaneous_seconds > 0:
                add("POSSIBLE_SIMULTANEOUS_SPEECH",
                    f"{sp.simultaneous_seconds:.2f} s waarin het model twee sprekers tegelijk actief meldt.")
            n_amb = sum(w.status == "AMBIGUOUS" for w in sp.words)
            if n_amb:
                add("AMBIGUOUS_WORD_SPEAKERS", f"{n_amb} woord(en) overlappen meerdere sprekers; niet toegewezen.")
            if roles is not None:
                unknown = [s for s in sp.seconds_per_speaker
                           if role_by_speaker.get(s) is None
                           or role_by_speaker[s].identity_status in ("UNKNOWN", "NO_REFERENCE")]
                if unknown:
                    add("SPEAKER_IDENTITY_UNKNOWN", f"Docentidentiteit onbekend voor: {unknown}.")
        vc = voice_by_id.get(seg.id)
        if vc is not None and vc.verdict == "CLOSER_TO_OTHER_SPEAKER":
            add("VOICE_CLOSER_TO_OTHER_SPEAKER",
                f"Stem lijkt meer op {vc.other_speaker} ({vc.other_similarity}) dan op {vc.speaker} ({vc.own_similarity}). "
                "Alleen een waarneming; luister zelf na.")
        if alignment is not None and alignment.status in (StepStatus.SUCCEEDED, StepStatus.PARTIAL):
            aligned = next((a for a in alignment.segments if a.segment_id == seg.id), None)
            if aligned is not None and aligned.status != StepStatus.SUCCEEDED:
                add("WORDS_NOT_FULLY_ALIGNED", f"Woorduitlijning van dit segment: {aligned.status.value}.")

        if any(s.code == "EMPTY_TEXT" for s in sigs):
            status = ReviewStatus.NOT_ASSESSABLE
        elif sigs:
            status = ReviewStatus.REVIEW_REQUIRED
        else:
            status = ReviewStatus.ASSESSABLE
        report.segments.append(SegmentQuality(segment_id=seg.id, status=status, signals=sigs))
    return report
