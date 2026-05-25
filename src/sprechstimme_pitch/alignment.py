"""Segment-to-score-event alignment.

Two alternative strategies are provided:

- :func:`recompute_times` — duration-weighted division of the segment's
  total span across its mapped score events. Pure metadata-only; does
  not consume the audio.
- :func:`auto_align_dtw` — 1-D dynamic-programming alignment that
  consumes the per-frame f0 trace and finds the optimal monotonic
  segmentation of frames onto notes. Useful when the performer's
  note durations diverge sharply from the score (e.g. speech-extreme
  Sprechstimme delivery on the Stiedry-Wagner 1940 demo recording).
"""

from __future__ import annotations

import csv
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import numpy as np

__all__ = [
    "SegmentKey",
    "ScoreEventKey",
    "recompute_times",
    "auto_align_dtw",
    "MAX_COST_CENT",
    "NEUTRAL_COST_CENT",
    "LAMBDA_DUR",
]


# Defaults for auto_align_dtw, calibrated on the Stiedry-Wagner 1940 demo.
MAX_COST_CENT = 1200.0
NEUTRAL_COST_CENT = 300.0
LAMBDA_DUR = 500.0


@dataclass(frozen=True)
class SegmentKey:
    recording_id: str
    segment_id: str


@dataclass(frozen=True)
class ScoreEventKey:
    piece_id: str
    bar_number: str
    note_index: str


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    """Read CSV file and return (fieldnames, rows)."""
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        if reader.fieldnames is None:
            raise ValueError(f"missing header: {path}")
        return list(reader.fieldnames), rows


def _write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, str]]) -> None:
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
    segments_rows: list[dict[str, str]],
    score_events_rows: list[dict[str, str]],
    map_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
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
    segments: dict[SegmentKey, tuple[str, float, float]] = {}
    for row in segments_rows:
        key = SegmentKey(row["recording_id"], row["segment_id"])
        segments[key] = (
            row["piece_id"],
            _to_float(row["start_s"], what=f"segments.start_s {key}"),
            _to_float(row["end_s"], what=f"segments.end_s {key}"),
        )

    # Build duration lookup: (piece_id, bar_number, note_index) → duration_qn
    durations: dict[ScoreEventKey, float] = {}
    for row in score_events_rows:
        key = ScoreEventKey(row["piece_id"], row["bar_number"], row["note_index"])
        durations[key] = _to_float(row["duration_qn"], what=f"score_events.duration_qn {key}")

    # Group mapping rows by segment
    grouped: dict[SegmentKey, list[dict[str, str]]] = {}
    for row in map_rows:
        skey = SegmentKey(row["recording_id"], row["segment_id"])
        grouped.setdefault(skey, []).append(row)

    updated_rows: list[dict[str, str]] = []

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
        weights: list[float] = []
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


def auto_align_dtw(
    obs_cent: np.ndarray,
    obs_reliable: np.ndarray,
    notated_cent: np.ndarray,
    notated_dur_qn: np.ndarray,
    *,
    max_cost_cent: float = MAX_COST_CENT,
    neutral_cost_cent: float = NEUTRAL_COST_CENT,
    lambda_dur: float = LAMBDA_DUR,
) -> tuple[np.ndarray, np.ndarray]:
    """Optimal monotonic segmentation of N pYIN frames onto M score notes.

    Solves a 1-D dynamic-programming alignment that assigns each frame of
    an observed f0 series to exactly one notated score note, with a
    per-note quadratic duration prior derived from the score's
    ``duration_qn`` weights. The objective minimised is::

        J = sum_m [ sum_{j in note m} cost(m, j)
                    + lambda_dur * (L_m - E_m)^2 / E_m ]

    where ``cost(m, j) = min(|obs_cent[j] - notated_cent[m]|, max_cost_cent)``
    when frame ``j`` is reliable and ``neutral_cost_cent`` otherwise, and
    ``E_m`` is the expected note length in frames derived from
    ``notated_dur_qn``.

    Useful as an alternative to :func:`recompute_times` when the
    performer's note durations diverge sharply from the score's notated
    values, as in speech-extreme Sprechstimme delivery. Unlike
    :func:`recompute_times` (pure duration-weighted division), this
    function consumes the actual pitch trace and is therefore
    audio-dependent — callers must compute ``obs_cent`` /
    ``obs_reliable`` from the segment's pYIN output first.

    Args:
        obs_cent: per-frame observed pitch in cents, shape ``(N,)``.
            NaN values are treated as unreliable regardless of the mask.
        obs_reliable: per-frame reliability mask, shape ``(N,)``.
            Conventionally ``voiced_flag & (voiced_prob >= 0.5)`` from
            :func:`sprechstimme_pitch.pitch.track_pitch`.
        notated_cent: per-note notated pitch in cents, shape ``(M,)``.
        notated_dur_qn: per-note duration in quarter notes, shape ``(M,)``.
            Used to derive the duration prior; must be strictly positive.
        max_cost_cent: cap on the per-frame reliable cost (default 1200,
            one octave).
        neutral_cost_cent: cost assigned to unreliable frames (default
            300). Lets the DP pass through silent/noisy stretches
            without distorting the path.
        lambda_dur: strength of the duration prior (default 500).
            Without this term the DP can collapse a long score note to
            a single frame whenever the reliable f0 trace contains a
            brief best-match window for that pitch.

    Returns:
        Tuple ``(start_idx, end_idx)`` of int arrays, shape ``(M,)``
        each. Both are inclusive frame indices into ``obs_cent``, with
        ``start_idx[0] == 0`` and ``end_idx[-1] == N - 1``.

    Raises:
        ValueError: if there are fewer frames than notes (``N < M``), or
            if any ``notated_dur_qn`` value is non-positive.
    """
    obs_cent = np.asarray(obs_cent, dtype=float)
    obs_reliable = np.asarray(obs_reliable, dtype=bool)
    notated_cent = np.asarray(notated_cent, dtype=float)
    notated_dur_qn = np.asarray(notated_dur_qn, dtype=float)

    n_frames = int(obs_cent.shape[0])
    n_notes = int(notated_cent.shape[0])
    if n_frames < n_notes:
        raise ValueError(f"too few frames ({n_frames}) for {n_notes} notes")
    if not np.all(notated_dur_qn > 0):
        raise ValueError("notated_dur_qn must be strictly positive")

    diff = np.abs(obs_cent.reshape(1, -1) - notated_cent.reshape(-1, 1))
    reliable_cost = np.minimum(diff, max_cost_cent)
    cost = np.where(
        obs_reliable.reshape(1, -1) & ~np.isnan(diff),
        reliable_cost,
        neutral_cost_cent,
    )
    prefix = np.cumsum(cost, axis=1)

    total_qn = float(notated_dur_qn.sum())
    exp_frames = np.maximum(n_frames * notated_dur_qn / total_qn, 1.0)

    inf = float("inf")
    dp = np.full((n_notes, n_frames), inf)
    bt = np.full((n_notes, n_frames), -1, dtype=int)

    # Note 0 must start at frame 0; length = j + 1
    for j in range(n_frames):
        length = j + 1
        pen = lambda_dur * (length - exp_frames[0]) ** 2 / exp_frames[0]
        dp[0, j] = float(prefix[0, j]) + pen

    for m in range(1, n_notes):
        for j in range(m, n_frames):
            ks = np.arange(m - 1, j)
            lengths = (j - ks).astype(float)
            durpen = lambda_dur * (lengths - exp_frames[m]) ** 2 / exp_frames[m]
            cand = dp[m - 1, ks] + (prefix[m, j] - prefix[m, ks]) + durpen
            idx = int(np.argmin(cand))
            dp[m, j] = float(cand[idx])
            bt[m, j] = int(ks[idx])

    end_idx = np.empty(n_notes, dtype=int)
    end_idx[n_notes - 1] = n_frames - 1
    for m in range(n_notes - 1, 0, -1):
        end_idx[m - 1] = bt[m, end_idx[m]]
    start_idx = np.empty(n_notes, dtype=int)
    start_idx[0] = 0
    for m in range(1, n_notes):
        start_idx[m] = end_idx[m - 1] + 1
    return start_idx, end_idx
