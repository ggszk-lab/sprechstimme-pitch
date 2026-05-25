"""Unit tests for sprechstimme_pitch.alignment."""

from __future__ import annotations

import numpy as np
import pytest

from sprechstimme_pitch.alignment import auto_align_dtw, recompute_times


def _segments() -> list[dict]:
    return [
        {
            "recording_id": "rec1",
            "segment_id": "seg1",
            "piece_id": "p1",
            "start_s": "10.0",
            "end_s": "16.0",
        }
    ]


def _score_events() -> list[dict]:
    return [
        {"piece_id": "p1", "bar_number": "1", "note_index": "1", "duration_qn": "1"},
        {"piece_id": "p1", "bar_number": "1", "note_index": "2", "duration_qn": "2"},
        {"piece_id": "p1", "bar_number": "1", "note_index": "3", "duration_qn": "3"},
    ]


def _map() -> list[dict]:
    return [
        {"recording_id": "rec1", "segment_id": "seg1", "bar_number": "1",
         "note_index": "1", "start_s": "0", "end_s": "0"},
        {"recording_id": "rec1", "segment_id": "seg1", "bar_number": "1",
         "note_index": "2", "start_s": "0", "end_s": "0"},
        {"recording_id": "rec1", "segment_id": "seg1", "bar_number": "1",
         "note_index": "3", "start_s": "0", "end_s": "0"},
    ]


def test_duration_weighted_distribution() -> None:
    out = recompute_times(
        segments_rows=_segments(),
        score_events_rows=_score_events(),
        map_rows=_map(),
    )
    # span = 6 s, weights 1:2:3 -> 1, 2, 3 seconds
    assert float(out[0]["start_s"]) == pytest.approx(10.0)
    assert float(out[0]["end_s"]) == pytest.approx(11.0)
    assert float(out[1]["start_s"]) == pytest.approx(11.0)
    assert float(out[1]["end_s"]) == pytest.approx(13.0)
    assert float(out[2]["start_s"]) == pytest.approx(13.0)
    assert float(out[2]["end_s"]) == pytest.approx(16.0)


def test_last_end_pinned_to_segment_end() -> None:
    out = recompute_times(
        segments_rows=_segments(),
        score_events_rows=_score_events(),
        map_rows=_map(),
    )
    assert float(out[-1]["end_s"]) == pytest.approx(16.0)


def test_missing_segment_raises() -> None:
    bad_map = _map()
    bad_map[0]["recording_id"] = "rec_unknown"
    with pytest.raises(ValueError, match="segment not found"):
        recompute_times(
            segments_rows=_segments(),
            score_events_rows=_score_events(),
            map_rows=bad_map,
        )


def test_non_positive_segment_duration_raises() -> None:
    segments = _segments()
    segments[0]["end_s"] = "10.0"
    with pytest.raises(ValueError, match="non-positive segment duration"):
        recompute_times(
            segments_rows=segments,
            score_events_rows=_score_events(),
            map_rows=_map(),
        )


# --- auto_align_dtw -----------------------------------------------------------


def test_auto_align_dtw_step_function() -> None:
    """Two notes [6000, 7000] cent across 10 reliable frames split 5/5 at the step."""
    obs_cent = np.array([6000.0] * 5 + [7000.0] * 5)
    obs_reliable = np.ones(10, dtype=bool)
    notated_cent = np.array([6000.0, 7000.0])
    notated_dur_qn = np.array([1.0, 1.0])

    start_idx, end_idx = auto_align_dtw(
        obs_cent, obs_reliable, notated_cent, notated_dur_qn
    )

    assert (start_idx[0], end_idx[0]) == (0, 4)
    assert (start_idx[1], end_idx[1]) == (5, 9)


def test_auto_align_dtw_duration_prior_prevents_collapse() -> None:
    """With equal score durations, the DP should not collapse any note to 1 frame
    even when the reliable f0 trace matches one note for most of the span."""
    # 60 frames all at 6000c; 3 notes at 6000c with equal duration_qn.
    # All notes have cost 0 throughout, so without a duration prior the DP
    # could collapse two notes to one frame each; with the prior, lengths
    # should be near 20 each.
    obs_cent = np.full(60, 6000.0)
    obs_reliable = np.ones(60, dtype=bool)
    notated_cent = np.array([6000.0, 6000.0, 6000.0])
    notated_dur_qn = np.array([1.0, 1.0, 1.0])

    start_idx, end_idx = auto_align_dtw(
        obs_cent, obs_reliable, notated_cent, notated_dur_qn
    )
    lengths = end_idx - start_idx + 1
    assert (lengths >= 10).all(), f"some note collapsed: lengths={lengths}"
    assert lengths.sum() == 60


def test_auto_align_dtw_handles_unreliable_frames() -> None:
    """Unreliable frames in the middle should be distributed by the duration
    prior, not absorbed into one note."""
    # Note 0 at 6000c, note 1 at 7000c, equal duration.
    # Frames 0-9: 6000c reliable. Frames 10-19: NaN/unreliable. Frames 20-29: 7000c reliable.
    obs_cent = np.concatenate([
        np.full(10, 6000.0),
        np.full(10, np.nan),
        np.full(10, 7000.0),
    ])
    obs_reliable = np.concatenate([
        np.ones(10, dtype=bool),
        np.zeros(10, dtype=bool),
        np.ones(10, dtype=bool),
    ])
    notated_cent = np.array([6000.0, 7000.0])
    notated_dur_qn = np.array([1.0, 1.0])

    start_idx, end_idx = auto_align_dtw(
        obs_cent, obs_reliable, notated_cent, notated_dur_qn
    )
    # With equal expected lengths of 15 frames each, the boundary should
    # land near frame 14/15 (within the unreliable gap).
    assert start_idx[0] == 0
    assert end_idx[1] == 29
    assert 9 <= end_idx[0] <= 19, f"boundary outside unreliable gap: end_idx[0]={end_idx[0]}"


def test_auto_align_dtw_too_few_frames_raises() -> None:
    with pytest.raises(ValueError, match="too few frames"):
        auto_align_dtw(
            obs_cent=np.array([6000.0, 7000.0]),
            obs_reliable=np.ones(2, dtype=bool),
            notated_cent=np.array([6000.0, 7000.0, 8000.0]),
            notated_dur_qn=np.array([1.0, 1.0, 1.0]),
        )


def test_auto_align_dtw_non_positive_duration_raises() -> None:
    with pytest.raises(ValueError, match="strictly positive"):
        auto_align_dtw(
            obs_cent=np.full(10, 6000.0),
            obs_reliable=np.ones(10, dtype=bool),
            notated_cent=np.array([6000.0, 7000.0]),
            notated_dur_qn=np.array([1.0, 0.0]),
        )
