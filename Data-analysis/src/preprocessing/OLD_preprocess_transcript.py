import re
from pathlib import Path


def remove_timestamps(line):
    return re.sub(r"^\d{2}:\d{2}\s*", "", line).strip()


def clean_transcript(lines):
    cleaned_lines = []

    for line in lines:
        clean_line = remove_timestamps(line)

        if clean_line:
            cleaned_lines.append(clean_line)

    full_text = " ".join(cleaned_lines)
    full_text = re.sub(r"\s+", " ", full_text).strip()

    return full_text


def split_into_sentences(text):
    sentences = re.split(r"(?<=[.!?])\s+", text)

    return [
        sentence.strip()
        for sentence in sentences
        if sentence.strip()
    ]


def extract_questions(sentences):
    return [
        sentence
        for sentence in sentences
        if "?" in sentence
    ]


if __name__ == "__main__":
    BASE_DIR = Path(__file__).resolve().parents[3]

    file_path = (
        BASE_DIR
        / "Data-local"
        / "raw"
        / "Breinschade_Uitleg_Sara.txt"
    )

    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    full_text = clean_transcript(lines)
    sentences = split_into_sentences(full_text)

    for i, sentence in enumerate(sentences[:30], start=1):
        print(f"{i}. {sentence}")