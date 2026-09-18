from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

SILENCE_START_RE = re.compile(r"silence_start:\s*([0-9.]+)")
SILENCE_END_RE = re.compile(r"silence_end:\s*([0-9.]+)")


@dataclass(frozen=True)
class Segment:
    start: float
    end: float

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)

    def as_dict(self) -> dict[str, float]:
        return {
            "start_seconds": round(self.start, 3),
            "end_seconds": round(self.end, 3),
            "duration": round(self.duration, 3),
        }


def _silences_from_ffmpeg(
    path: Path,
    duration: float,
    noise_db: float = -35.0,
    silence_duration: float = 1.2,
) -> list[Segment]:
    command = [
        "ffmpeg",
        "-hide_banner",
        "-nostats",
        "-i",
        str(path),
        "-vn",
        "-af",
        f"silencedetect=noise={noise_db}dB:d={silence_duration}",
        "-f",
        "null",
        "-",
    ]
    process = subprocess.run(command, check=False, capture_output=True, text=True)
    if process.returncode != 0:
        raise RuntimeError(process.stderr[-3000:] or "FFmpeg-Audioanalyse fehlgeschlagen")

    starts = [float(x) for x in SILENCE_START_RE.findall(process.stderr)]
    ends = [float(x) for x in SILENCE_END_RE.findall(process.stderr)]

    silences: list[Segment] = []
    end_index = 0
    for start in starts:
        while end_index < len(ends) and ends[end_index] < start:
            end_index += 1
        end = ends[end_index] if end_index < len(ends) else duration
        if end > start:
            silences.append(Segment(max(0.0, start), min(duration, end)))
        end_index += 1

    return silences


def _non_silent_segments(duration: float, silences: list[Segment]) -> list[Segment]:
    if duration <= 0:
        return []

    segments: list[Segment] = []
    cursor = 0.0
    for silence in sorted(silences, key=lambda item: item.start):
        if silence.start > cursor:
            segments.append(Segment(cursor, silence.start))
        cursor = max(cursor, silence.end)
    if cursor < duration:
        segments.append(Segment(cursor, duration))
    return segments


def _merge_segments(segments: list[Segment], max_gap: float) -> list[Segment]:
    if not segments:
        return []

    merged = [segments[0]]
    for segment in segments[1:]:
        previous = merged[-1]
        gap = segment.start - previous.end
        if gap <= max_gap:
            merged[-1] = Segment(previous.start, max(previous.end, segment.end))
        else:
            merged.append(segment)
    return merged


def detect_speech_candidates(
    path: Path,
    duration: float,
    *,
    noise_db: float = -35.0,
    silence_duration: float = 1.2,
    merge_gap: float = 12.0,
    min_speech: float = 20.0,
    padding: float = 2.0,
) -> list[dict[str, float]]:
    """Return candidate speech blocks based on long-form audio activity.

    This first-stage detector deliberately produces editorial suggestions rather
    than making publishing decisions. Music and applause can still count as
    activity; later versions can add VAD/transcription/speaker signals.
    """
    silences = _silences_from_ffmpeg(path, duration, noise_db, silence_duration)
    active = _non_silent_segments(duration, silences)
    merged = _merge_segments(active, merge_gap)

    result: list[Segment] = []
    for segment in merged:
        if segment.duration < min_speech:
            continue
        start = max(0.0, segment.start - padding)
        end = min(duration, segment.end + padding)
        result.append(Segment(start, end))

    return [segment.as_dict() for segment in result]
