"""pYIN pitch tracking and reliability flagging.

This module provides:

- :func:`track_pitch`             — wrapper around ``librosa.pyin``.
- :func:`note_voiced_ratio`       — fraction of voiced frames in a slice.
- :func:`note_f0_iqr_cent`        — interquartile range of voiced f0
  (in cents, relative to A4).
- :func:`classify_pitch_class_error` — categorise a per-note error as
  octave / fifth / within (subharmonic detection).
- :func:`is_pyin_unreliable`      — combine the above into a boolean flag
  with a human-readable reasons string.

The reliability spec follows issue #12 in the research repository:
a note is *unreliable* when **any** of these hold:

1. ``voiced_ratio < voiced_ratio_threshold`` (default ``0.5``)
2. ``f0_iqr_cent > f0_iqr_threshold_cent`` (default ``500``)
3. The per-note error matches a subharmonic pitch-class
   (``oct_1`` / ``oct_2`` / ``fifth_down`` / ``fifth_up``) within
   ``pitch_class_error_tol_cent`` (default ``50``).

The intent is to filter pYIN locking errors, not the performer's
intentional musical deviation.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import stats

__all__ = [
    "PitchTrack",
    "track_pitch",
    "note_voiced_ratio",
    "note_f0_iqr_cent",
    "classify_pitch_class_error",
    "is_pyin_unreliable",
    "cent_to_hz",
    "hz_to_cent",
    "VOICED_RATIO_THRESHOLD",
    "F0_IQR_THRESHOLD_CENT",
    "PITCH_CLASS_ERROR_TOL_CENT",
]


VOICED_RATIO_THRESHOLD = 0.5
F0_IQR_THRESHOLD_CENT = 500.0
PITCH_CLASS_ERROR_TOL_CENT = 50.0


@dataclass
class PitchTrack:
    """Output of :func:`track_pitch`.

    All three arrays are aligned frame-by-frame.

    Attributes
    ----------
    f0_hz
        Fundamental frequency in Hz; ``NaN`` for unvoiced frames.
    voiced_flag
        ``1.0`` if voiced, ``0.0`` otherwise.
    voiced_probs
        Per-frame voicing probability.
    """

    f0_hz: np.ndarray
    voiced_flag: np.ndarray
    voiced_probs: np.ndarray


def track_pitch(
    y: np.ndarray,
    sr: float,
    fmin: float = 130.8,  # C3
    fmax: float = 1046.5,  # C6
    frame_length: int = 2048,
    hop_length: int = 256,
) -> PitchTrack:
    """Run ``librosa.pyin`` and wrap the output.

    Defaults match the paper-1 corpus configuration.
    """
    import librosa

    f0_hz, voiced_flag, voiced_probs = librosa.pyin(
        y,
        fmin=fmin,
        fmax=fmax,
        sr=sr,
        frame_length=frame_length,
        hop_length=hop_length,
    )
    return PitchTrack(f0_hz=f0_hz, voiced_flag=voiced_flag, voiced_probs=voiced_probs)


def note_voiced_ratio(voiced_flag: np.ndarray) -> float:
    """Fraction of voiced frames within a note slice.

    Returns ``NaN`` when the slice is empty.
    """
    voiced_flag = np.asarray(voiced_flag, dtype=float)
    if voiced_flag.size == 0:
        return float("nan")
    return float(np.nanmean(voiced_flag))


def note_f0_iqr_cent(f0_hz: np.ndarray, voiced_flag: np.ndarray) -> float:
    """IQR of the voiced f0 within a note slice, expressed in cents.

    Cents are computed relative to A4 (``440 Hz``); IQR is invariant to
    the reference, so any consistent reference works.

    Returns ``NaN`` when the slice has no voiced frames.
    """
    f0_hz = np.asarray(f0_hz, dtype=float)
    voiced_flag = np.asarray(voiced_flag, dtype=float)
    voiced = f0_hz[voiced_flag > 0.5]
    voiced = voiced[~np.isnan(voiced) & (voiced > 0)]
    if voiced.size == 0:
        return float("nan")
    cents = 1200.0 * np.log2(voiced / 440.0)
    return float(stats.iqr(cents))


def classify_pitch_class_error(
    err_cent: float,
    tol: float = PITCH_CLASS_ERROR_TOL_CENT,
) -> str:
    """Classify a per-note error into pYIN-typical subharmonic categories.

    Returns one of:

    - ``"oct_1"``      : ``|err_cent| ≈ 1200 ± tol``
    - ``"oct_2"``      : ``|err_cent| ≈ 2400 ± tol``
    - ``"fifth_down"`` : ``err_cent ≈ -700 ± tol``
    - ``"fifth_up"``   : ``err_cent ≈ +700 ± tol``
    - ``"within"``     : none of the above
    - ``"nan"``        : ``err_cent`` is NaN
    """
    if err_cent is None or (isinstance(err_cent, float) and np.isnan(err_cent)):
        return "nan"
    if abs(err_cent + 700) <= tol:
        return "fifth_down"
    if abs(err_cent - 700) <= tol:
        return "fifth_up"
    abs_err = abs(err_cent)
    for k in (1, 2):
        if abs(abs_err - 1200 * k) <= tol:
            return f"oct_{k}"
    return "within"


def is_pyin_unreliable(
    voiced_ratio: float,
    f0_iqr_cent: float,
    pitch_class_error: str,
    *,
    voiced_ratio_threshold: float = VOICED_RATIO_THRESHOLD,
    f0_iqr_threshold_cent: float = F0_IQR_THRESHOLD_CENT,
) -> tuple[bool, str]:
    """Decide whether a note's pYIN estimate should be treated as unreliable.

    Inputs are the precomputed scalar diagnostics for a single note
    (use :func:`note_voiced_ratio`, :func:`note_f0_iqr_cent`,
    :func:`classify_pitch_class_error` to derive them).

    Parameters
    ----------
    voiced_ratio
        Fraction of voiced frames in the note. ``NaN`` is treated as
        "no estimate" and flags the note as unreliable.
    f0_iqr_cent
        IQR of voiced f0 in cents.
    pitch_class_error
        Output of :func:`classify_pitch_class_error`.

    Returns
    -------
    (is_unreliable, reasons)
        ``reasons`` is a comma-separated string drawn from
        ``{"no_estimate", "voiced_low", "iqr_high",
        "pitch_class_<oct_1|oct_2|fifth_down|fifth_up>"}``,
        empty when the note is reliable.
    """
    reasons: list[str] = []

    if voiced_ratio is None or (isinstance(voiced_ratio, float) and np.isnan(voiced_ratio)):
        reasons.append("no_estimate")
    else:
        if voiced_ratio < voiced_ratio_threshold:
            reasons.append("voiced_low")
        if (
            f0_iqr_cent is not None
            and not (isinstance(f0_iqr_cent, float) and np.isnan(f0_iqr_cent))
            and f0_iqr_cent > f0_iqr_threshold_cent
        ):
            reasons.append("iqr_high")

    if pitch_class_error not in ("within", "nan", "", None):
        reasons.append(f"pitch_class_{pitch_class_error}")

    return (len(reasons) > 0, ",".join(reasons))


def cent_to_hz(cents: float, ref_hz: float = 440.0) -> float:
    """Convert cents (relative to ``ref_hz``) to Hz."""
    return ref_hz * (2.0 ** (cents / 1200.0))


def hz_to_cent(hz: float, ref_hz: float = 440.0) -> float:
    """Convert Hz to cents (relative to ``ref_hz``)."""
    return 1200.0 * np.log2(hz / ref_hz)
