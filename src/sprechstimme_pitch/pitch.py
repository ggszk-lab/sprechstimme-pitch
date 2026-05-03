"""pYIN pitch tracking and reliability flagging.

Provides a wrapper around librosa.pyin for tracking fundamental frequency
with voicing confidence, and a flag function to mark unreliable pitch
estimates based on voicing ratio, F0 variability, and octave/subharmonic errors.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import stats


@dataclass
class PitchTrack:
    """Results of pYIN pitch tracking.

    Attributes:
        f0_hz: fundamental frequency in Hz (may be NaN for unvoiced frames)
        voiced_flag: binary voicing confidence (1.0 = voiced, 0.0 = unvoiced)
        voiced_probs: probability of voicing per frame
    """

    f0_hz: np.ndarray
    voiced_flag: np.ndarray
    voiced_probs: np.ndarray


def track_pitch(
    y: np.ndarray,
    sr: float,
    fmin: float = 130.8,  # C3
    fmax: float = 523.3,  # C5
    frame_length: int = 2048,
    hop_length: int = 256,
) -> PitchTrack:
    """
    Track fundamental frequency using pYIN.

    Args:
        y: audio time series (mono)
        sr: sample rate (Hz)
        fmin: minimum frequency (Hz, default C3 = 130.8 Hz)
        fmax: maximum frequency (Hz, default C5 = 523.3 Hz)
        frame_length: FFT window length
        hop_length: number of samples between successive frames

    Returns:
        PitchTrack with f0_hz, voiced_flag, voiced_probs.
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

    return PitchTrack(
        f0_hz=f0_hz,
        voiced_flag=voiced_flag,
        voiced_probs=voiced_probs,
    )


def is_pyin_unreliable(
    f0_hz: np.ndarray,
    voiced_flag: np.ndarray,
    voiced_ratio_threshold: float = 0.5,
    f0_iqr_threshold_cent: float = 500.0,
    pitch_class_error_notes: list[str] | None = None,
    abs_error_cent: float | None = None,
    pitch_class_error_tol_cent: float = 50.0,
) -> bool:
    """
    Flag a note's pitch estimate as unreliable based on pYIN diagnostics.

    A note is marked unreliable if ANY of these conditions hold:

    1. Voicing ratio (fraction of voiced frames) < voiced_ratio_threshold
    2. IQR of voiced F0 > f0_iqr_threshold_cent
    3. Error belongs to subharmonic/octave error pitch class (±1200/±2400/±700 ±tol)

    Args:
        f0_hz: pitch track for this note (Hz), may contain NaN
        voiced_flag: voicing flags (0.0/1.0) for each frame
        voiced_ratio_threshold: min voicing ratio to pass (default 0.5)
        f0_iqr_threshold_cent: max IQR of F0 in cents (default 500)
        pitch_class_error_notes: list of detected pitch-class error strings
            (e.g. ['oct_1', 'fifth_down']), or None if no errors detected
        abs_error_cent: absolute error for this note in cents, or None if NaN
        pitch_class_error_tol_cent: tolerance for matching error patterns (cents)

    Returns:
        True if unreliable (any condition met), False otherwise.
    """
    reasons: list[str] = []

    # Condition 1: voiced ratio
    voiced_ratio = float(np.nanmean(voiced_flag)) if voiced_flag.size > 0 else 0.0
    if voiced_ratio < voiced_ratio_threshold:
        reasons.append("voiced_low")

    # Condition 2: F0 IQR
    f0_voiced = f0_hz[voiced_flag > 0.5]
    if f0_voiced.size > 0:
        f0_cent = 1200.0 * np.log2(f0_voiced / 440.0)
        iqr = float(stats.iqr(f0_cent, nan_policy="omit"))
        if iqr > f0_iqr_threshold_cent:
            reasons.append("iqr_high")

    # Condition 3: pitch-class error (subharmonic/octave)
    if pitch_class_error_notes is not None and abs_error_cent is not None:
        subharmonic_errors = {"oct_1", "oct_2", "fifth_down", "fifth_up"}
        for err in pitch_class_error_notes:
            if err in subharmonic_errors:
                reasons.append(f"pitch_class_{err}")
                break  # Mark unreliable; don't list all errors

    return len(reasons) > 0


def cent_to_hz(cents: float, ref_hz: float = 440.0) -> float:
    """Convert cents (relative to A4) to Hz."""
    return ref_hz * (2.0 ** (cents / 1200.0))


def hz_to_cent(hz: float, ref_hz: float = 440.0) -> float:
    """Convert Hz to cents (relative to A4)."""
    return 1200.0 * np.log2(hz / ref_hz)
