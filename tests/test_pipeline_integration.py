"""End-to-end pipeline test on synthetic audio.

Synthesizes sine tones that follow ``score_events.csv`` inside the
ath-1973 note windows, writes a wav, and runs the full
``analyse_recording`` pipeline on it. This guards the wiring the unit
tests cannot see: metadata joins, note windowing, the pYIN frequency
range (m8 contains a D5 at 587 Hz, above the old C5 cap), the
reliability filter, and the classifier.

Runtime is a few pYIN calls over ~15 s of audio per scenario.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import soundfile as sf

from sprechstimme_pitch import analyse_recording, config, metrics

REPO_ROOT = Path(__file__).resolve().parents[1]
METADATA_DIR = REPO_ROOT / "data" / "metadata"
RECORDING_ID = "ath-1973"
PIECE_NO = 7


@pytest.fixture(scope="module")
def metadata():
    segments = pd.read_csv(METADATA_DIR / "segments.csv")
    score_events = pd.read_csv(METADATA_DIR / "score_events.csv")
    seg_map = pd.read_csv(METADATA_DIR / "segment_score_map.csv")
    segments = segments[segments["piece_id"].astype(int) == PIECE_NO]
    score_events = score_events[score_events["piece_id"].astype(int) == PIECE_NO]
    return segments, score_events, seg_map


def _synthesize(metadata, offset_cent: float, path: Path) -> None:
    """Write a wav of sine tones at the notated pitches (+offset) inside
    each ath-1973 note window; silence elsewhere."""
    segments, score_events, seg_map = metadata
    sr = config.SR_PYIN
    rec_map = seg_map[seg_map["recording_id"] == RECORDING_ID].merge(
        score_events[["bar_number", "note_index", "ref_pitch_cent"]],
        on=["bar_number", "note_index"],
        how="inner",
    )
    total_s = float(
        segments[segments["recording_id"] == RECORDING_ID]["end_s"].max()
    ) + 0.5
    y = np.zeros(int(total_s * sr), dtype=np.float32)
    fade = int(0.01 * sr)
    for _, n in rec_map.iterrows():
        i0 = int(float(n["start_s"]) * sr)
        i1 = int(float(n["end_s"]) * sr)
        if i1 <= i0:
            continue
        cent = float(n["ref_pitch_cent"]) + offset_cent
        freq = 440.0 * 2.0 ** ((cent - 6900.0) / 1200.0)
        t = np.arange(i1 - i0) / sr
        tone = 0.3 * np.sin(2.0 * np.pi * freq * t).astype(np.float32)
        env = np.ones_like(tone)
        env[:fade] = np.linspace(0.0, 1.0, fade)
        env[-fade:] = np.linspace(1.0, 0.0, fade)
        y[i0:i1] = tone * env
    sf.write(path, y, sr)


def _run(metadata, offset_cent: float, tmp_dir: Path):
    segments, score_events, seg_map = metadata
    wav = tmp_dir / f"synthetic_{int(offset_cent)}.wav"
    _synthesize(metadata, offset_cent, wav)
    return analyse_recording(
        wav, RECORDING_ID, segments, seg_map, score_events,
    )


@pytest.fixture(scope="module")
def score_exact(metadata, tmp_path_factory):
    return _run(metadata, 0.0, tmp_path_factory.mktemp("synth"))


@pytest.fixture(scope="module")
def transposed_down(metadata, tmp_path_factory):
    # -600 cents: far beyond the 400-cent offset threshold, but safely
    # outside the +/-700 and +/-1200 subharmonic windows of the
    # reliability filter (a -700 shift would be flagged as fifth_down).
    return _run(metadata, -600.0, tmp_path_factory.mktemp("synth"))


def test_metadata_covers_recording(metadata):
    segments, score_events, seg_map = metadata
    assert not segments[segments["recording_id"] == RECORDING_ID].empty
    assert not score_events.empty
    assert not seg_map[seg_map["recording_id"] == RECORDING_ID].empty


def test_score_exact_is_score_faithful(score_exact):
    metrics_list, notes = score_exact
    assert len(metrics_list) == 4  # four voice segments (m10-11 has no notes)
    assert not notes["is_pyin_unreliable"].any(), (
        "clean sines must pass the reliability filter"
    )
    for m in metrics_list:
        assert abs(m.register_offset_cent) < 20
        assert m.contour_correlation > 0.99
    agg = metrics.aggregate_metrics(metrics_list)
    assert (
        metrics.classify_performance(
            register_offset_cent=agg["register_offset_cent"],
            contour_std=agg["contour_correlation_std"],
        )
        == "score-faithful"
    )


def test_high_notes_tracked(score_exact):
    """m8's D5 (587 Hz) must be tracked — fails under an fmax of C5."""
    _, notes = score_exact
    d5 = notes[(notes["bar_number"] == 8) & (notes["ref_cent"] == 7400.0)]
    assert not d5.empty
    assert (d5["err_cent"].abs() < 50).all()


def test_transposed_down_is_directed_recitation(transposed_down):
    metrics_list, notes = transposed_down
    assert len(metrics_list) == 4
    agg = metrics.aggregate_metrics(metrics_list)
    assert agg["register_offset_cent"] == pytest.approx(-600, abs=30)
    assert (
        metrics.classify_performance(
            register_offset_cent=agg["register_offset_cent"],
            contour_std=agg["contour_correlation_std"],
        )
        == "directed-recitation"
    )
