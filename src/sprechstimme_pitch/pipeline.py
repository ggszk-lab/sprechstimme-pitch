"""Batch pipeline: metadata + audio -> per-note diagnostics -> three-axis metrics.

This is the programmatic core of ``notebooks/02_paper_reproduction.ipynb``:
given one recording's audio file and the three metadata tables, it runs
pYIN per segment, derives per-note reliability diagnostics, and computes
the three-axis metrics on the reliable subset. Keeping it in the package
(rather than notebook cells) makes it importable from tests.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from . import config, metrics, pitch


def cents_from_hz(hz: np.ndarray | float) -> np.ndarray | float:
    """Convert Hz to cents with A4 = 440 Hz = 6900 cents (MIDI 69)."""
    return 1200.0 * np.log2(hz / 440.0) + 6900.0


def analyse_segment(
    audio_path: Path | str,
    seg_row: pd.Series,
    segment_score_map_df: pd.DataFrame,
    score_events_df: pd.DataFrame,
    *,
    sr: int = config.SR_PYIN,
    fmin: float = config.FMIN_HZ,
    fmax: float = config.FMAX_HZ,
    frame_length: int = config.FRAME_LENGTH,
    hop_length: int = config.HOP_LENGTH,
    min_notes: int = 3,
) -> tuple[metrics.ThreeAxisMetrics, pd.DataFrame] | None:
    """Analyse one (recording, segment) pair.

    Loads the segment's audio slice (resampled to ``sr``, mono), runs
    pYIN, derives per-note diagnostics (voiced ratio, F0 IQR, median
    pitch, reliability flag), and computes the three-axis metrics on the
    reliable subset. Returns ``None`` when the segment has no notes or
    no audio inside its window.
    """
    import librosa

    rec_id = seg_row["recording_id"]
    seg_id = seg_row["segment_id"]

    start_s = float(seg_row["start_s"])
    dur_s = float(seg_row["end_s"]) - start_s
    if dur_s <= 0:
        return None
    y, sr = librosa.load(
        str(audio_path), sr=sr, mono=True, offset=start_s, duration=dur_s,
    )
    if y.size == 0:
        return None

    track = pitch.track_pitch(
        y, sr, fmin=fmin, fmax=fmax,
        frame_length=frame_length, hop_length=hop_length,
    )

    seg_map = segment_score_map_df[
        (segment_score_map_df["recording_id"] == rec_id)
        & (segment_score_map_df["segment_id"] == seg_id)
    ].sort_values(["bar_number", "note_index"]).reset_index(drop=True)

    note_rows = []
    hop_s = hop_length / sr
    for _, n in seg_map.iterrows():
        rel_start = float(n["start_s"]) - start_s
        rel_end = float(n["end_s"]) - start_s
        i0 = max(0, int(rel_start / hop_s))
        i1 = min(len(track.f0_hz), max(i0 + 1, int(rel_end / hop_s)))
        f0_slice = track.f0_hz[i0:i1]
        v_slice = track.voiced_flag[i0:i1]

        voiced_ratio = pitch.note_voiced_ratio(v_slice)
        f0_iqr = pitch.note_f0_iqr_cent(f0_slice, v_slice)

        f0_voiced = f0_slice[(v_slice > 0.5) & ~np.isnan(f0_slice) & (f0_slice > 0)]
        est_cent = (
            float(np.median(cents_from_hz(f0_voiced))) if f0_voiced.size > 0 else np.nan
        )

        score_match = score_events_df[
            (score_events_df["bar_number"] == int(n["bar_number"]))
            & (score_events_df["note_index"] == int(n["note_index"]))
        ]
        ref_cent = (
            float(score_match.iloc[0]["ref_pitch_cent"]) if len(score_match) > 0 else np.nan
        )
        err_cent = (
            est_cent - ref_cent
            if not (np.isnan(est_cent) or np.isnan(ref_cent)) else np.nan
        )

        pc_err = pitch.classify_pitch_class_error(err_cent)
        unreliable, reasons = pitch.is_pyin_unreliable(
            voiced_ratio=voiced_ratio,
            f0_iqr_cent=f0_iqr,
            pitch_class_error=pc_err,
        )

        note_rows.append({
            "recording_id": rec_id,
            "segment_id": seg_id,
            "bar_number": int(n["bar_number"]),
            "note_index": int(n["note_index"]),
            "est_cent": est_cent,
            "ref_cent": ref_cent,
            "err_cent": err_cent,
            "voiced_ratio": voiced_ratio,
            "f0_iqr_cent": f0_iqr,
            "pitch_class_error": pc_err,
            "is_pyin_unreliable": unreliable,
            "unreliable_reasons": reasons,
        })

    notes_df = pd.DataFrame(note_rows)
    if notes_df.empty:
        return None

    m = metrics.compute_three_axis_metrics(
        est_cent=notes_df["est_cent"].to_numpy(),
        score_cent=notes_df["ref_cent"].to_numpy(),
        unreliable_flags=notes_df["is_pyin_unreliable"].to_numpy(),
        min_notes=min_notes,
    )
    return m, notes_df


def analyse_recording(
    audio_path: Path | str,
    recording_id: str,
    segments_df: pd.DataFrame,
    segment_score_map_df: pd.DataFrame,
    score_events_df: pd.DataFrame,
    **kwargs,
) -> tuple[list[metrics.ThreeAxisMetrics], pd.DataFrame]:
    """Run :func:`analyse_segment` over every segment of one recording.

    Returns the list of per-segment metrics and the concatenated
    per-note diagnostics table (empty when nothing was analysable —
    e.g. the flute-only reference segment, which has no mapped notes).
    """
    metrics_list: list[metrics.ThreeAxisMetrics] = []
    notes_frames: list[pd.DataFrame] = []
    rec_segments = segments_df[segments_df["recording_id"] == recording_id]
    for _, seg_row in rec_segments.iterrows():
        result = analyse_segment(
            audio_path, seg_row, segment_score_map_df, score_events_df, **kwargs,
        )
        if result is None:
            continue
        m, notes_df = result
        metrics_list.append(m)
        notes_frames.append(notes_df)
    all_notes = (
        pd.concat(notes_frames, ignore_index=True) if notes_frames else pd.DataFrame()
    )
    return metrics_list, all_notes
