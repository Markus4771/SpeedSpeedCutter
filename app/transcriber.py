from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from faster_whisper import WhisperModel


@lru_cache(maxsize=3)
def _model(model_size: str, compute_type: str) -> WhisperModel:
    return WhisperModel(model_size, device="cpu", compute_type=compute_type)


def transcribe_with_vad(
    path: Path,
    *,
    model_size: str = "small",
    language: str = "de",
    compute_type: str = "int8",
    min_silence_ms: int = 1200,
) -> dict[str, Any]:
    """Transcribe speech and use Silero VAD through faster-whisper.

    Returns only detected speech segments. This helps suppress music/noise-only
    sections, while the editor remains responsible for the final cut.
    """
    model = _model(model_size, compute_type)
    segments, info = model.transcribe(
        str(path),
        language=language or None,
        beam_size=5,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": min_silence_ms},
        word_timestamps=False,
        condition_on_previous_text=True,
    )

    output = []
    for segment in segments:
        text = segment.text.strip()
        if not text:
            continue
        output.append(
            {
                "start_seconds": round(float(segment.start), 3),
                "end_seconds": round(float(segment.end), 3),
                "duration": round(float(segment.end - segment.start), 3),
                "text": text,
            }
        )

    return {
        "language": info.language,
        "language_probability": round(float(info.language_probability), 4),
        "segments": output,
    }


def merge_transcript_segments(
    segments: list[dict[str, Any]],
    *,
    merge_gap: float = 12.0,
    min_duration: float = 20.0,
    padding: float = 2.0,
    total_duration: float | None = None,
) -> list[dict[str, Any]]:
    if not segments:
        return []

    merged: list[dict[str, Any]] = []
    for segment in segments:
        current = {
            "start_seconds": float(segment["start_seconds"]),
            "end_seconds": float(segment["end_seconds"]),
            "text": str(segment.get("text", "")).strip(),
        }
        if merged and current["start_seconds"] - merged[-1]["end_seconds"] <= merge_gap:
            merged[-1]["end_seconds"] = max(merged[-1]["end_seconds"], current["end_seconds"])
            merged[-1]["text"] = (merged[-1]["text"] + " " + current["text"]).strip()
        else:
            merged.append(current)

    result = []
    for item in merged:
        raw_duration = item["end_seconds"] - item["start_seconds"]
        if raw_duration < min_duration:
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
                "text": item["text"],
            }
        )
    return result
