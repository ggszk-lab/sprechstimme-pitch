"""Three-axis (register / range / contour) analysis of Sprechstimme pitch.

Public API
----------
Top-level re-exports for the most common entry points. Submodule imports
remain available (``from sprechstimme_pitch.plotting import ...``).

Pitch tracking and reliability:
    :func:`track_pitch`, :func:`is_pyin_unreliable`,
    :func:`classify_pitch_class_error`, :func:`note_voiced_ratio`,
    :func:`note_f0_iqr_cent`

Three-axis metrics:
    :func:`compute_three_axis_metrics`, :func:`aggregate_metrics`,
    :func:`classify_performance`, :class:`ThreeAxisMetrics`

Alignment:
    :func:`recompute_times`
"""

from __future__ import annotations

from .alignment import recompute_times
from .metrics import (
    THRESHOLD_CONTOUR_STD,
    THRESHOLD_OFFSET_ABS_CENT,
    ThreeAxisMetrics,
    aggregate_metrics,
    classify_performance,
    compute_three_axis_metrics,
)
from .pitch import (
    F0_IQR_THRESHOLD_CENT,
    PITCH_CLASS_ERROR_TOL_CENT,
    VOICED_RATIO_THRESHOLD,
    PitchTrack,
    classify_pitch_class_error,
    is_pyin_unreliable,
    note_f0_iqr_cent,
    note_voiced_ratio,
    track_pitch,
)

__version__ = "0.1.0"

__all__ = [
    "__version__",
    # pitch
    "PitchTrack",
    "track_pitch",
    "note_voiced_ratio",
    "note_f0_iqr_cent",
    "classify_pitch_class_error",
    "is_pyin_unreliable",
    "VOICED_RATIO_THRESHOLD",
    "F0_IQR_THRESHOLD_CENT",
    "PITCH_CLASS_ERROR_TOL_CENT",
    # metrics
    "ThreeAxisMetrics",
    "compute_three_axis_metrics",
    "aggregate_metrics",
    "classify_performance",
    "THRESHOLD_CONTOUR_STD",
    "THRESHOLD_OFFSET_ABS_CENT",
    # alignment
    "recompute_times",
]
