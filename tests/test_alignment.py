"""Unit tests for sprechstimme_pitch.alignment.recompute_times."""

from __future__ import annotations

import pytest

from sprechstimme_pitch.alignment import recompute_times


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
