"""Unit tests for sprechstimme_pitch.metrics."""

from __future__ import annotations

import numpy as np
import pytest

from sprechstimme_pitch.metrics import (
    THRESHOLD_CONTOUR_STD,
    THRESHOLD_OFFSET_ABS_CENT,
    ThreeAxisMetrics,
    aggregate_metrics,
    classify_performance,
    compute_three_axis_metrics,
)


def test_perfect_match_yields_zero_offset_unit_range_unit_contour() -> None:
    score = np.array([6000.0, 6200.0, 6400.0, 6700.0, 7000.0])
    est = score.copy()

    m = compute_three_axis_metrics(est, score)

    assert m.register_offset_cent == pytest.approx(0.0)
    assert m.range_compression == pytest.approx(1.0)
    assert m.contour_correlation == pytest.approx(1.0)
    assert m.n_notes_used == 5


def test_register_offset_is_median_of_est_minus_score() -> None:
    score = np.array([6000.0, 6200.0, 6400.0])
    est = score + np.array([100.0, 100.0, 200.0])

    m = compute_three_axis_metrics(est, score)

    assert m.register_offset_cent == pytest.approx(100.0)


def test_range_compression_is_std_ratio_not_peak_to_peak() -> None:
    # Choose values that distinguish std-based vs peak-to-peak ratio.
    # score: std = sqrt(var of [0, 200, 400, 600, 800]) = 282.84
    # est:   doubled spacing -> std = 565.68
    # std ratio = 2.0; peak-to-peak ratio also = 2.0 here.
    # Use asymmetric perturbation so the two definitions diverge.
    score = np.array([0.0, 100.0, 100.0, 100.0, 200.0])
    est = np.array([0.0, 50.0, 50.0, 50.0, 200.0])  # narrower around middle
    # score peak-to-peak = 200, est peak-to-peak = 200 -> ratio 1.0
    # but std(score) = sqrt((100-100)^2*3 + 100^2*2)/5 = sqrt(20000/5) = 63.25
    # and std(est)  = sqrt(50^2 + 50^2 + 50^2 + 50^2 + 150^2)/5
    #              = sqrt((2500*4 + 22500)/5) = sqrt(32500/5) = 80.62
    # std ratio ~= 1.275, clearly not 1.0
    m = compute_three_axis_metrics(est, score)

    score_pp = float(np.max(score) - np.min(score))
    est_pp = float(np.max(est) - np.min(est))
    std_ratio = float(np.std(est, ddof=0) / np.std(score, ddof=0))
    pp_ratio = est_pp / score_pp

    assert m.range_compression == pytest.approx(std_ratio, rel=1e-9)
    assert m.range_compression != pytest.approx(pp_ratio, abs=0.01)


def test_unreliable_flags_are_excluded() -> None:
    score = np.array([6000.0, 6200.0, 6400.0, 6600.0])
    est = np.array([6000.0, 6200.0, 6400.0, 9999.0])  # last is bogus
    flags = np.array([False, False, False, True])

    m = compute_three_axis_metrics(est, score, unreliable_flags=flags)

    assert m.n_notes_used == 3
    assert m.register_offset_cent == pytest.approx(0.0)


def test_too_few_notes_returns_nan_for_range_and_contour() -> None:
    score = np.array([6000.0, 6200.0])
    est = np.array([6000.0, 6200.0])

    m = compute_three_axis_metrics(est, score, min_notes=3)

    assert m.n_notes_used == 2
    assert not np.isnan(m.register_offset_cent)
    assert np.isnan(m.range_compression)
    assert np.isnan(m.contour_correlation)


def test_constant_score_yields_nan_range_compression() -> None:
    score = np.array([6000.0, 6000.0, 6000.0])
    est = np.array([6000.0, 6100.0, 6200.0])

    m = compute_three_axis_metrics(est, score)

    assert np.isnan(m.range_compression)


def test_zero_variance_intervals_avoid_spearmanr_nan_warning() -> None:
    # score intervals all equal -> spearmanr is undefined.
    # The function should detect this and return NaN cleanly without
    # raising or emitting a runtime warning.
    score = np.array([6000.0, 6200.0, 6400.0, 6600.0])
    est = np.array([6050.0, 6210.0, 6390.0, 6605.0])

    m = compute_three_axis_metrics(est, score)

    assert np.isnan(m.contour_correlation)


def test_aggregate_uses_nanmedian() -> None:
    metrics_list = [
        ThreeAxisMetrics(100.0, 1.0, 0.8, 5),
        ThreeAxisMetrics(200.0, 1.2, 0.9, 5),
        ThreeAxisMetrics(float("nan"), float("nan"), float("nan"), 0),
    ]
    agg = aggregate_metrics(metrics_list)

    assert agg["register_offset_cent"] == pytest.approx(150.0)
    assert agg["range_compression"] == pytest.approx(1.1)
    assert agg["contour_correlation_median"] == pytest.approx(0.85)


def test_classify_performance_dynamic_takes_priority() -> None:
    # Large offset AND high contour_std -> dynamic wins.
    assert (
        classify_performance(
            register_offset_cent=THRESHOLD_OFFSET_ABS_CENT + 100,
            contour_std=THRESHOLD_CONTOUR_STD + 0.1,
        )
        == "dynamic"
    )


def test_classify_performance_directed_recitation() -> None:
    assert (
        classify_performance(
            register_offset_cent=THRESHOLD_OFFSET_ABS_CENT + 100,
            contour_std=0.1,
        )
        == "directed-recitation"
    )


def test_classify_performance_score_faithful() -> None:
    assert (
        classify_performance(register_offset_cent=50.0, contour_std=0.1)
        == "score-faithful"
    )
