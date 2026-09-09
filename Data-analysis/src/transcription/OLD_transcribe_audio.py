from faster_whisper import WhisperModel, BatchedInferencePipeline
from pathlib import Path


def transcribe_audio(audio_path):
    model = WhisperModel(
        "base",
        device="cpu",
        compute_type="int8"
    )

    batched_model = BatchedInferencePipeline(model=model)

    segments, info = batched_model.transcribe(
        str(audio_path),
        language="nl",
        vad_filter=True,
        batch_size=8
    )

    results = []

    for segment in segments:
        results.append({
            "start": segment.start,
            "end": segment.end,
            "text": segment.text.strip()
        })

    return results


if __name__ == "__main__":
    BASE_DIR = Path(__file__).resolve().parents[3]

    audio_path = (
        BASE_DIR
        / "Data-local"
        / "raw"
        / "breinschade.mp3"
    )

    transcript = transcribe_audio(audio_path)

    for segment in transcript[:30]:
        print(
            f"[{segment['start']:.2f} - {segment['end']:.2f}] "
            f"{segment['text']}"
        )

    output_path = (
        BASE_DIR
        / "Data-local"
        / "processed"
        / "breinschade_transcript.txt"
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        for segment in transcript:
            f.write(
                f"[{segment['start']:.2f} - {segment['end']:.2f}] "
                f"{segment['text']}\n"
            )

    print(f"\nTranscript opgeslagen in: {output_path}")