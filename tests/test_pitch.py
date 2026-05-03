"""Unit tests for sprechstimme_pitch.pitch reliability helpers."""

from __future__ import annotations

import numpy as np

from sprechstimme_pitch.pitch import (
    classify_pitch_class_error,
    is_pyin_unreliable,
    note_f0_iqr_cent,
    note_voiced_ratio,
)


def test_voiced_ratio_basic() -> None:
    assert note_voiced_ratio(np.array([1.0, 1.0, 0.0, 0.0])) == 0.5
    assert note_voiced_ratio(np.array([1.0, 1.0, 1.0])) == 1.0
    assert note_voiced_ratio(np.array([0.0, 0.0])) == 0.0


def test_voiced_ratio_empty_is_nan() -> None:
    assert np.isnan(note_voiced_ratio(np.array([])))


def test_iqr_uses_voiced_only_in_cents() -> None:
    # Five voiced frames spanning 0..1200 cents in 300-cent steps.
    # Q1 = 300, Q3 = 900 -> IQR = 600 cents.
    f0_voiced = np.array([440.0, 523.25, 622.25, 739.99, 880.0])  # 0, 300, 600, 900, 1200 cents
    f0 = np.concatenate([f0_voiced, np.array([100.0, 100.0])])  # add unvoiced junk
    voiced = np.concatenate([np.ones(5), np.zeros(2)])
    iqr = note_f0_iqr_cent(f0, voiced)
    assert 595.0 < iqr < 605.0


def test_classify_pitch_class_error_octaves_and_fifths() -> None:
    assert classify_pitch_class_error(1200) == "oct_1"
    assert classify_pitch_class_error(-1200) == "oct_1"
    assert classify_pitch_class_error(2400) == "oct_2"
    assert classify_pitch_class_error(-700) == "fifth_down"
    assert classify_pitch_class_error(700) == "fifth_up"
    assert classify_pitch_class_error(50) == "within"  # boundary, falls within
    assert classify_pitch_class_error(0) == "within"
    assert classify_pitch_class_error(float("nan")) == "nan"


def test_classify_uses_tolerance() -> None:
    assert classify_pitch_class_error(1240, tol=50) == "oct_1"  # within 50c
    assert classify_pitch_class_error(1260, tol=50) == "within"  # outside 50c


def test_is_pyin_unreliable_voiced_low() -> None:
    flag, reasons = is_pyin_unreliable(
        voiced_ratio=0.3, f0_iqr_cent=100.0, pitch_class_error="within"
    )
    assert flag is True
    assert "voiced_low" in reasons


def test_is_pyin_unreliable_iqr_high() -> None:
    flag, reasons = is_pyin_unreliable(
        voiced_ratio=1.0, f0_iqr_cent=600.0, pitch_class_error="within"
    )
    assert flag is True
    assert "iqr_high" in reasons


def test_is_pyin_unreliable_pitch_class() -> None:
    flag, reasons = is_pyin_unreliable(
        voiced_ratio=1.0, f0_iqr_cent=100.0, pitch_class_error="oct_1"
    )
    assert flag is True
    assert "pitch_class_oct_1" in reasons


def test_is_pyin_unreliable_no_estimate_when_voiced_ratio_nan() -> None:
    flag, reasons = is_pyin_unreliable(
        voiced_ratio=float("nan"),
        f0_iqr_cent=float("nan"),
        pitch_class_error="nan",
    )
    assert flag is True
    assert "no_estimate" in reasons


def test_is_pyin_unreliable_combined_reasons() -> None:
    flag, reasons = is_pyin_unreliable(
        voiced_ratio=0.3, f0_iqr_cent=600.0, pitch_class_error="oct_2"
    )
    assert flag is True
    parts = reasons.split(",")
    assert "voiced_low" in parts
    assert "iqr_high" in parts
    assert "pitch_class_oct_2" in parts


def test_is_pyin_unreliable_clean_note() -> None:
    flag, reasons = is_pyin_unreliable(
        voiced_ratio=1.0, f0_iqr_cent=100.0, pitch_class_error="within"
    )
    assert flag is False
    assert reasons == ""
