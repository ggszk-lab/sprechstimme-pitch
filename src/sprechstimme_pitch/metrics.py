"""Three-axis metrics: register, range, contour decomposition.

Decomposes a performer's deviation from the score into three independent
axes:

- **register** (offset)      — overall pitch shift, in cents
- **range** (compression)    — ratio of pitch-spread (std obs / std score)
- **contour** (direction)    — Spearman correlation of adjacent intervals

Definitions follow ``register_normalized_metrics.ipynb`` in the original
research repository.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.stats import spearmanr

__all__ = [
    "ThreeAxisMetrics",
    "compute_three_axis_metrics",
    "aggregate_metrics",
    "classify_performance",
    "THRESHOLD_CONTOUR_STD",
    "THRESHOLD_OFFSET_ABS_CENT",
]


# Type-classification thresholds (set from observed values across the
# 5-recording paper-1 corpus; see decisions log in the research repository).
THRESHOLD_CONTOUR_STD = 0.3
THRESHOLD_OFFSET_ABS_CENT = 400.0


@dataclass
class ThreeAxisMetrics:
    """Three-axis decomposition of pitch deviation for one segment.

    Attributes
    ----------
    register_offset_cent
        Median ``est - score`` over reliable notes.
    range_compression
        ``std(est) / std(score)`` over reliable notes (population std,
        ``ddof=0``). NaN when ``n_notes_used`` < ``min_notes`` or when the
        score has no spread.
    contour_correlation
        Spearman ρ of adjacent intervals (``np.diff``) of est vs. score.
        NaN when either side has zero variance.
    n_notes_used
        Number of reliable notes (``unreliable_flags == False``) used.
    """

    register_offset_cent: float
    range_compression: float
    contour_correlation: float
    n_notes_used: int


def _safe_std(xs: np.ndarray) -> float:
    """Population std over non-NaN values; NaN if fewer than 2 valid points."""
    xs = xs[~np.isnan(xs)]
    if xs.size < 2:
        return float("nan")
    return float(np.std(xs, ddof=0))


def compute_three_axis_metrics(
    est_cent: np.ndarray,
    score_cent: np.ndarray,
    unreliable_flags: np.ndarray | None = None,
    min_notes: int = 3,
) -> ThreeAxisMetrics:
    """Compute the three-axis metrics for one segment.

    Parameters
    ----------
    est_cent
        Per-note observed pitch in cents.
    score_cent
        Per-note score pitch in cents.
    unreliable_flags
        Boolean array; ``True`` excludes the corresponding note from
        all three calculations. ``None`` keeps every note.
    min_notes
        Minimum reliable notes required to compute ``range_compression``
        and ``contour_correlation``. ``register_offset_cent`` requires
        only one reliable note.
    """
    est_cent = np.asarray(est_cent, dtype=float)
    score_cent = np.asarray(score_cent, dtype=float)
    if est_cent.shape != score_cent.shape:
        raise ValueError(
            f"shape mismatch: est_cent {est_cent.shape} vs score_cent {score_cent.shape}"
        )

    if unreliable_flags is None:
        mask = np.ones(est_cent.shape, dtype=bool)
    else:
        unreliable_flags = np.asarray(unreliable_flags, dtype=bool)
        if unreliable_flags.shape != est_cent.shape:
            raise ValueError(
                f"unreliable_flags shape mismatch: {unreliable_flags.shape} vs {est_cent.shape}"
            )
        mask = ~unreliable_flags

    valid = mask & ~np.isnan(est_cent) & ~np.isnan(score_cent)
    est_kept = est_cent[valid]
    score_kept = score_cent[valid]
    n_kept = int(est_kept.size)

    register_offset_cent = (
        float(np.median(est_kept - score_kept)) if n_kept >= 1 else float("nan")
    )

    if n_kept >= min_notes:
        std_est = _safe_std(est_kept)
        std_score = _safe_std(score_kept)
        if np.isnan(std_score) or std_score == 0:
            range_compression = float("nan")
        else:
            range_compression = std_est / std_score
    else:
        range_compression = float("nan")

    contour_correlation = float("nan")
    if n_kept >= min_notes:
        est_intervals = np.diff(est_kept)
        score_intervals = np.diff(score_kept)
        if est_intervals.size > 0 and np.std(est_intervals) > 0 and np.std(score_intervals) > 0:
            rho, _ = spearmanr(est_intervals, score_intervals)
            contour_correlation = float(rho) if not np.isnan(rho) else float("nan")

    return ThreeAxisMetrics(
        register_offset_cent=register_offset_cent,
        range_compression=range_compression,
        contour_correlation=contour_correlation,
        n_notes_used=n_kept,
    )


def aggregate_metrics(
    metrics_list: list[ThreeAxisMetrics],
) -> dict[str, float]:
    """Aggregate per-segment metrics to per-recording level.

    Returns a dict with:

    - ``register_offset_cent``         — median across segments
    - ``range_compression``            — median across segments
    - ``contour_correlation_median``   — median across segments
    - ``contour_correlation_std``      — std across segments (used for
      the dynamic-type axis)
    """
    if not metrics_list:
        raise ValueError("empty metrics list")

    register_arr = np.array([m.register_offset_cent for m in metrics_list], dtype=float)
    range_arr = np.array([m.range_compression for m in metrics_list], dtype=float)
    contour_arr = np.array([m.contour_correlation for m in metrics_list], dtype=float)

    return {
        "register_offset_cent": float(np.nanmedian(register_arr)),
        "range_compression": float(np.nanmedian(range_arr)),
        "contour_correlation_median": float(np.nanmedian(contour_arr)),
        "contour_correlation_std": float(np.nanstd(contour_arr, ddof=0)),
    }


def classify_performance(
    register_offset_cent: float,
    contour_std: float,
    *,
    contour_std_threshold: float = THRESHOLD_CONTOUR_STD,
    offset_abs_threshold_cent: float = THRESHOLD_OFFSET_ABS_CENT,
) -> str:
    """Classify a recording into a performance type.

    Decision order matches the original
    ``performer_classification.ipynb`` flowchart:

    1. ``contour_std > contour_std_threshold`` → ``'dynamic'``
    2. else ``|register_offset| > offset_abs_threshold_cent`` →
       ``'directed-recitation'``
    3. else → ``'score-faithful'``

    Parameters
    ----------
    register_offset_cent
        Per-recording aggregate (``aggregate_metrics`` →
        ``register_offset_cent``).
    contour_std
        Per-recording aggregate (``aggregate_metrics`` →
        ``contour_correlation_std``).
    """
    abs_offset = (
        abs(register_offset_cent) if not np.isnan(register_offset_cent) else 0.0
    )
    c_std = contour_std if not np.isnan(contour_std) else 0.0

    if c_std > contour_std_threshold:
        return "dynamic"
    if abs_offset > offset_abs_threshold_cent:
        return "directed-recitation"
    return "score-faithful"
