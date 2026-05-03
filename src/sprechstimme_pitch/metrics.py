"""Three-axis metrics: register, range, contour decomposition.

Decomposes the deviation of a performer's pitch from the score into
three independent dimensions:

- register (offset): overall pitch shift
- range (compression): pitch span expansion/compression
- contour (direction): adherence to pitch shape
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.stats import spearmanr


@dataclass
class ThreeAxisMetrics:
    """Three-axis decomposition of pitch deviation.

    Attributes:
        register_offset_cent: median pitch difference (estimate - score)
        range_compression: ratio of observed to score pitch span
        contour_correlation: Spearman correlation of adjacent pitch intervals
        n_notes_used: number of notes included in calculation
    """

    register_offset_cent: float
    range_compression: float
    contour_correlation: float
    n_notes_used: int


def compute_three_axis_metrics(
    est_cent: np.ndarray,
    score_cent: np.ndarray,
    unreliable_flags: np.ndarray | None = None,
    min_notes: int = 3,
) -> ThreeAxisMetrics:
    """
    Compute three-axis metrics for a voice segment.

    Args:
        est_cent: observed pitch in cents (per note)
        score_cent: score pitch in cents (per note)
        unreliable_flags: boolean array (True = exclude from calculation),
            e.g. from is_pyin_unreliable. If None, all notes are used.
        min_notes: minimum number of reliable notes to compute range/contour
            (register is computed if at least 1 note remains)

    Returns:
        ThreeAxisMetrics with register_offset_cent, range_compression,
        contour_correlation, and n_notes_used.
    """
    if len(est_cent) != len(score_cent):
        raise ValueError(f"mismatched lengths: {len(est_cent)} vs {len(score_cent)}")

    # Apply unreliability filter
    if unreliable_flags is None:
        mask = np.ones(len(est_cent), dtype=bool)
    else:
        if len(unreliable_flags) != len(est_cent):
            raise ValueError(f"unreliable_flags length mismatch: {len(unreliable_flags)}")
        mask = ~unreliable_flags

    est_kept = est_cent[mask]
    score_kept = score_cent[mask]
    n_kept = len(est_kept)

    # Register: median offset (requires ≥1 note)
    register_offset_cent = float('nan')
    if n_kept >= 1:
        register_offset_cent = float(np.nanmedian(est_kept - score_kept))

    # Range: ratio of pitch spans (requires ≥min_notes)
    range_compression = float('nan')
    if n_kept >= min_notes:
        est_span = float(np.nanmax(est_kept) - np.nanmin(est_kept))
        score_span = float(np.nanmax(score_kept) - np.nanmin(score_kept))
        if score_span > 0:
            range_compression = est_span / score_span
        else:
            range_compression = float('nan')

    # Contour: Spearman correlation of adjacent intervals (requires ≥min_notes+1)
    contour_correlation = float('nan')
    if n_kept >= min_notes:
        # Adjacent pitch differences (intervals)
        est_intervals = np.diff(est_kept)
        score_intervals = np.diff(score_kept)
        if len(est_intervals) > 0:
            r, _ = spearmanr(est_intervals, score_intervals, nan_policy='propagate')
            contour_correlation = float(r) if not np.isnan(r) else float('nan')

    return ThreeAxisMetrics(
        register_offset_cent=register_offset_cent,
        range_compression=range_compression,
        contour_correlation=contour_correlation,
        n_notes_used=n_kept,
    )


def aggregate_metrics(
    metrics_list: list[ThreeAxisMetrics],
    agg_fn: str = 'median',
) -> dict[str, float]:
    """
    Aggregate per-segment metrics to per-recording level.

    Args:
        metrics_list: list of ThreeAxisMetrics (one per segment)
        agg_fn: 'median' or 'mean'

    Returns:
        dict with keys like 'register_offset_cent', 'range_compression',
        'contour_correlation_median', 'contour_correlation_std'
    """
    if not metrics_list:
        raise ValueError("empty metrics list")

    agg = np.median if agg_fn == 'median' else np.mean

    register_values = [m.register_offset_cent for m in metrics_list]
    range_values = [m.range_compression for m in metrics_list]
    contour_values = [m.contour_correlation for m in metrics_list]

    return {
        'register_offset_cent': float(agg(np.array(register_values))),
        'range_compression': float(agg(np.array(range_values))),
        'contour_correlation_median': float(np.nanmedian(np.array(contour_values))),
        'contour_correlation_std': float(np.nanstd(np.array(contour_values))),
    }


def classify_performance(
    register_offset_cent: float,
    contour_correlation: float,
    register_threshold_cent: float = 400.0,
    contour_threshold: float = 0.3,
) -> str:
    """
    Classify a performance into a type based on three-axis thresholds.

    Rough classification:
    - 'score_faithful': register near zero, contour high
    - 'directed_recitation': register large (speech-like), contour moderate
    - 'dynamic': contour low (unstable/varied)

    Args:
        register_offset_cent: median pitch offset in cents
        contour_correlation: Spearman correlation of pitch contour
        register_threshold_cent: threshold for register classification
        contour_threshold: threshold for contour stability

    Returns:
        Classification string.
    """
    abs_register = abs(register_offset_cent) if not np.isnan(register_offset_cent) else 0
    has_large_register = abs_register > register_threshold_cent
    has_stable_contour = (
        not np.isnan(contour_correlation) and contour_correlation > contour_threshold
    )

    if has_large_register:
        return 'directed_recitation'
    elif has_stable_contour:
        return 'score_faithful'
    else:
        return 'dynamic'
