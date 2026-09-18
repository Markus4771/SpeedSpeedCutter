from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any


@lru_cache(maxsize=2)
def _pipeline(model_ref: str):
    try:
        from pyannote.audio import Pipeline
    except ImportError as exc:
        raise RuntimeError(
            "pyannote.audio ist nicht installiert. "
            "Installiere requirements-diarization.txt."
        ) from exc

    token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN")
    kwargs: dict[str, Any] = {}
    if token and not Path(model_ref).exists():
        kwargs["token"] = token

    try:
        return Pipeline.from_pretrained(model_ref, **kwargs)
    except Exception as exc:
        raise RuntimeError(
            "Diarisierungsmodell konnte nicht geladen werden. "
            "Für pyannote/speaker-diarization-community-1 müssen die "
            "Nutzungsbedingungen auf Hugging Face akzeptiert und HF_TOKEN "
            "gesetzt werden; alternativ kann SSC_DIARIZATION_MODEL auf einen "
            "lokalen Modellpfad zeigen."
        ) from exc


def diarize(
    path: Path,
    *,
    min_speakers: int | None = None,
    max_speakers: int | None = None,
) -> dict[str, Any]:
    model_ref = os.getenv(
        "SSC_DIARIZATION_MODEL",
        "pyannote/speaker-diarization-community-1",
    )
    pipeline = _pipeline(model_ref)

    options: dict[str, int] = {}
    if min_speakers is not None:
        options["min_speakers"] = min_speakers
    if max_speakers is not None:
        options["max_speakers"] = max_speakers

    output = pipeline(str(path), **options)

    annotation = getattr(output, "exclusive_speaker_diarization", None)
    if annotation is None:
        annotation = getattr(output, "speaker_diarization", output)

    turns = []
    speakers: set[str] = set()
    for turn, speaker in annotation:
        speaker_name = str(speaker)
        speakers.add(speaker_name)
        turns.append(
            {
                "start_seconds": round(float(turn.start), 3),
                "end_seconds": round(float(turn.end), 3),
                "duration": round(float(turn.end - turn.start), 3),
                "speaker": speaker_name,
            }
        )

    return {
        "model": model_ref,
        "speaker_count": len(speakers),
        "turns": turns,
    }


def speaker_blocks(
    turns: list[dict[str, Any]],
    *,
    min_turn_duration: float = 8.0,
    merge_same_speaker_gap: float = 4.0,
    padding: float = 1.5,
    total_duration: float | None = None,
) -> list[dict[str, Any]]:
    """Merge adjacent turns of the same speaker into editorial cut suggestions."""
    if not turns:
        return []

    merged: list[dict[str, Any]] = []
    for turn in turns:
        current = {
            "start_seconds": float(turn["start_seconds"]),
            "end_seconds": float(turn["end_seconds"]),
            "speaker": str(turn["speaker"]),
        }
        if (
            merged
            and merged[-1]["speaker"] == current["speaker"]
            and current["start_seconds"] - merged[-1]["end_seconds"] <= merge_same_speaker_gap
        ):
            merged[-1]["end_seconds"] = max(
                merged[-1]["end_seconds"], current["end_seconds"]
            )
        else:
            merged.append(current)

    result = []
    for item in merged:
        duration = item["end_seconds"] - item["start_seconds"]
        if duration < min_turn_duration:
            continue

        start = max(0.0, item["start_seconds"] - padding)
        end = item["end_seconds"] + padding
        if total_duration is not None:
            end = min(total_duration, end)

        result.append(
            {
                "start_seconds": round(start, 3),
                "end_seconds": round(end, 3),
                "duration": round(end - start, 3),
                "speaker": item["speaker"],
            }
        )

    return result
