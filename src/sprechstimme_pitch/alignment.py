"""Segment-to-score-event alignment.

Maps audio segments to score events using duration-weighted time division.
This is a lightweight approach suitable for pilot analysis; it does not
attempt full metrical alignment.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


@dataclass(frozen=True)
class SegmentKey:
    recording_id: str
    segment_id: str


@dataclass(frozen=True)
class ScoreEventKey:
    piece_id: str
    bar_number: str
    note_index: str


def _read_csv(path: Path) -> Tuple[List[str], List[Dict[str, str]]]:
    """Read CSV file and return (fieldnames, rows)."""
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        if reader.fieldnames is None:
            raise ValueError(f"missing header: {path}")
        return list(reader.fieldnames), rows


def _write_csv(path: Path, fieldnames: List[str], rows: Iterable[Dict[str, str]]) -> None:
    """Write CSV file."""
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _to_float(value: str, *, what: str) -> float:
    """Parse float or raise ValueError with context."""
    if value is None or value == "":
        raise ValueError(f"missing numeric value for {what}")
    try:
        return float(value)
    except ValueError as e:
        raise ValueError(f"invalid float for {what}: {value!r}") from e


def _fmt_seconds(value: float) -> str:
    """Format seconds to 3 decimal places (millisecond precision)."""
    return f"{value:.3f}"


def recompute_times(
    *,
    segments_rows: List[Dict[str, str]],
    score_events_rows: List[Dict[str, str]],
    map_rows: List[Dict[str, str]],
) -> List[Dict[str, str]]:
    """
    Recompute per-note start/end seconds in segment_score_map.

    Divides each segment's duration proportionally across its mapped score
    events using `score_events.duration_qn` as weights.

    Args:
        segments_rows: list of dicts from segments.csv
        score_events_rows: list of dicts from score_events.csv
        map_rows: list of dicts from segment_score_map.csv (pre-mapped sequence)

    Returns:
        Updated map_rows with recomputed start_s and end_s.

    Raises:
        ValueError: if required columns are missing or values are invalid.
    """
    # Build segment lookup: (recording_id, segment_id) → (piece_id, start_s, end_s)
    segments: Dict[SegmentKey, Tuple[str, float, float]] = {}
    for row in segments_rows:
        key = SegmentKey(row["recording_id"], row["segment_id"])
        segments[key] = (
            row["piece_id"],
            _to_float(row["start_s"], what=f"segments.start_s {key}"),
            _to_float(row["end_s"], what=f"segments.end_s {key}"),
        )

    # Build duration lookup: (piece_id, bar_number, note_index) → duration_qn
    durations: Dict[ScoreEventKey, float] = {}
    for row in score_events_rows:
        key = ScoreEventKey(row["piece_id"], row["bar_number"], row["note_index"])
        durations[key] = _to_float(row["duration_qn"], what=f"score_events.duration_qn {key}")

    # Group mapping rows by segment
    grouped: Dict[SegmentKey, List[Dict[str, str]]] = {}
    for row in map_rows:
        skey = SegmentKey(row["recording_id"], row["segment_id"])
        grouped.setdefault(skey, []).append(row)

    updated_rows: List[Dict[str, str]] = []

    for skey, rows in grouped.items():
        if skey not in segments:
            raise ValueError(f"segment not found in segments.csv: {skey}")
        piece_id, seg_start, seg_end = segments[skey]
        seg_span = seg_end - seg_start
        if seg_span <= 0:
            raise ValueError(f"non-positive segment duration for {skey}: {seg_span}")

        # Sort by bar_number, note_index
        rows_sorted = sorted(rows, key=lambda r: (int(r["bar_number"]), int(r["note_index"])))

        # Collect duration weights
        weights: List[float] = []
        for r in rows_sorted:
            ekey = ScoreEventKey(piece_id, r["bar_number"], r["note_index"])
            if ekey not in durations:
                raise ValueError(f"duration not found in score_events.csv for {ekey}")
            w = durations[ekey]
            if w <= 0:
                raise ValueError(f"non-positive duration_qn for {ekey}: {w}")
            weights.append(w)

        total_weight = sum(weights)
        if total_weight <= 0:
            raise ValueError(f"total duration_qn is non-positive for {skey}")

        # Distribute segment time proportionally
        cursor = seg_start
        for r, w in zip(rows_sorted, weights, strict=True):
            span = seg_span * (w / total_weight)
            start_s = cursor
            end_s = cursor + span
            cursor = end_s

            rr = dict(r)
            rr["start_s"] = _fmt_seconds(start_s)
            rr["end_s"] = _fmt_seconds(end_s)
            updated_rows.append(rr)

        # Ensure exact end (avoid rounding drift)
        if updated_rows:
            updated_rows[-1]["end_s"] = _fmt_seconds(seg_end)

    # Sort by (recording_id, segment_id, bar_number, note_index)
    updated_rows.sort(
        key=lambda r: (
            r["recording_id"],
            r["segment_id"],
            int(r["bar_number"]),
            int(r["note_index"]),
        )
    )
    return updated_rows
