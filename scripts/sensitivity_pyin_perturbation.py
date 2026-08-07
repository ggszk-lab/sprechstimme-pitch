#!/usr/bin/env python3
"""Robustness of the three-type classification to the estimation stage.

Two perturbations of the pitch-estimation stage itself:

  (a) a 3x3 grid over the pYIN analysis parameters
      (frame_length in {1024, 2048, 4096} samples, hop_length in
      {128, 256, 512}), and
  (b) onset perturbation of every note window under the baseline pYIN
      parameters: systematic shifts of +-20 ms and +-50 ms, and per-note
      uniform jitter of +-30 ms under three fixed random seeds.

For every configuration the full chain (pYIN -> per-note diagnostics ->
reliability filter -> three-axis metrics -> aggregation -> classification)
is re-run and the resulting type is compared with the published
classification.

Audio is NOT distributed with this repository. Place the recordings under
``data/audio/`` (see docs/data.md); Demucs-separated vocal stems at
``data/audio/separated/htdemucs/<name>/vocals.wav`` are preferred, matching
the paper pipeline. Recordings whose audio cannot be found are skipped
with a notice.

Input:  data/metadata/{segments,score_events,segment_score_map}.csv
        data/audio/...                       (user-supplied)
        results/classification_summary.csv   (published types; sanity gate)
Output: results/sensitivity/
  - pyin_perturbation_grid.csv      ... per config x recording: aggregates + type
  - pyin_perturbation_segments.csv  ... per config x segment: three-axis values

Sanity gate: the baseline cell (frame=2048, hop=256, no shift) must
reproduce the published type for every analysed recording.

Dependencies: the sprechstimme_pitch package (librosa, numpy, pandas).
Run: python scripts/sensitivity_pyin_perturbation.py
"""
from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sprechstimme_pitch import config, metrics, pitch  # noqa: E402
from sprechstimme_pitch.pipeline import cents_from_hz  # noqa: E402

META = ROOT / "data/metadata"
AUDIO_DIR = ROOT / "data/audio"
OUT = ROOT / "results/sensitivity"
OUT.mkdir(parents=True, exist_ok=True)
PUBLISHED_CLASSIFICATION = ROOT / "results/classification_summary.csv"

RECORDINGS = ["ath-1973", "hul-2012", "bou-1961", "bou-1977", "her-1991"]
VOICE_SEGMENTS = ["seg_p07_m5", "seg_p07_m8", "seg_p07_m13", "seg_p07_m18b6_m19b5"]

FRAME_GRID = [1024, 2048, 4096]
HOP_GRID = [128, 256, 512]
# Onset perturbation: systematic shift (all notes) and per-note uniform
# jitter with fixed seeds.
SHIFT_CONFIGS = [("shift-50ms", -0.050), ("shift-20ms", -0.020),
                 ("shift+20ms", +0.020), ("shift+50ms", +0.050)]
JITTER_CONFIGS = [("jitterU30ms-seed1", 1), ("jitterU30ms-seed2", 2),
                  ("jitterU30ms-seed3", 3)]
JITTER_HALF_WIDTH_S = 0.030

# Classification thresholds (same as the paper / sensitivity_e1.py)
THRESHOLD_CONTOUR_STD = 0.3
THRESHOLD_OFFSET_ABS = 400

# Extra audio loaded on both sides of each segment window so that shifted
# note windows stay inside the loaded slice.
PAD_S = 0.1

AUDIO_EXTS = (".wav", ".flac", ".mp3", ".m4a", ".ogg", ".aiff", ".aif")


def find_audio(recording_id: str) -> Path | None:
    """Best audio source for this recording (same order as notebook 02)."""
    sep_root = AUDIO_DIR / "separated" / "htdemucs"

    if sep_root.is_dir():
        for d in sorted(sep_root.iterdir()):
            if d.is_dir() and d.name.startswith(recording_id):
                v = d / "vocals.wav"
                if v.exists():
                    return v

    def _sep_or_raw(p: Path) -> Path:
        v = sep_root / p.stem / "vocals.wav"
        return v if v.exists() else p

    sub = AUDIO_DIR / recording_id
    if sub.is_dir():
        for ext in AUDIO_EXTS:
            for p in sorted(sub.glob(f"*{ext}")):
                return _sep_or_raw(p)

    for ext in AUDIO_EXTS:
        for p in sorted(AUDIO_DIR.glob(f"{recording_id}*{ext}")):
            return _sep_or_raw(p)

    return None


def std0(xs) -> float:
    xs = [x for x in xs if not (isinstance(x, float) and math.isnan(x))]
    if len(xs) < 2:
        return float("nan")
    m = sum(xs) / len(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / len(xs))  # population std


def median(xs) -> float:
    xs = sorted(x for x in xs if not (isinstance(x, float) and math.isnan(x)))
    if not xs:
        return float("nan")
    n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


def classify(contour_std: float, offset_abs: float) -> str:
    if not math.isnan(contour_std) and contour_std > THRESHOLD_CONTOUR_STD:
        return "dynamic"
    if not math.isnan(offset_abs) and offset_abs > THRESHOLD_OFFSET_ABS:
        return "directed-recitation"
    return "score-faithful"


def analyse_segment_windows(
    y: np.ndarray, sr: int, load_start_s: float,
    note_windows: list[tuple[int, int, float, float, float]],
    frame_length: int, hop_length: int,
) -> metrics.ThreeAxisMetrics:
    """Same procedure as pipeline.analyse_segment with the note windows
    passed in explicitly (so they can be shifted or jittered).

    note_windows: (bar_number, note_index, start_s, end_s, ref_cent)
    """
    track = pitch.track_pitch(
        y, sr, fmin=config.FMIN_HZ, fmax=config.FMAX_HZ,
        frame_length=frame_length, hop_length=hop_length,
    )
    hop_s = hop_length / sr
    est, ref, flags = [], [], []
    for _bar, _idx, n_start, n_end, ref_cent in note_windows:
        rel_start = n_start - load_start_s
        rel_end = n_end - load_start_s
        i0 = max(0, int(rel_start / hop_s))
        i1 = min(len(track.f0_hz), max(i0 + 1, int(rel_end / hop_s)))
        f0_slice = track.f0_hz[i0:i1]
        v_slice = track.voiced_flag[i0:i1]
        voiced_ratio = pitch.note_voiced_ratio(v_slice)
        f0_iqr = pitch.note_f0_iqr_cent(f0_slice, v_slice)
        f0_voiced = f0_slice[(v_slice > 0.5) & ~np.isnan(f0_slice) & (f0_slice > 0)]
        est_cent = (float(np.median(cents_from_hz(f0_voiced)))
                    if f0_voiced.size > 0 else np.nan)
        err = est_cent - ref_cent if not np.isnan(est_cent) else np.nan
        pc_err = pitch.classify_pitch_class_error(err)
        unreliable, _ = pitch.is_pyin_unreliable(
            voiced_ratio=voiced_ratio, f0_iqr_cent=f0_iqr, pitch_class_error=pc_err,
        )
        est.append(est_cent)
        ref.append(ref_cent)
        flags.append(unreliable)
    return metrics.compute_three_axis_metrics(
        est_cent=np.array(est), score_cent=np.array(ref),
        unreliable_flags=np.array(flags), min_notes=3,
    )


def main() -> None:
    import librosa

    segments = pd.read_csv(META / "segments.csv")
    score_events = pd.read_csv(META / "score_events.csv")
    seg_map = pd.read_csv(META / "segment_score_map.csv")

    with PUBLISHED_CLASSIFICATION.open(encoding="utf-8", newline="") as f:
        published_type = {r["recording_id"]: r["classified_type"]
                          for r in csv.DictReader(f)}

    recordings = []
    audio_paths = {}
    for rec in RECORDINGS:
        p = find_audio(rec)
        if p is None:
            print(f"skip {rec}: no audio found under data/audio/ "
                  "(see docs/data.md)")
            continue
        recordings.append(rec)
        audio_paths[rec] = p
    if not recordings:
        print("No audio found for any recording; nothing to do.")
        return

    def note_windows_for(rec: str, seg: str):
        rows = seg_map[(seg_map["recording_id"] == rec)
                       & (seg_map["segment_id"] == seg)].sort_values(
            ["bar_number", "note_index"])
        out = []
        for _, n in rows.iterrows():
            match = score_events[
                (score_events["bar_number"] == int(n["bar_number"]))
                & (score_events["note_index"] == int(n["note_index"]))]
            ref_cent = (float(match.iloc[0]["ref_pitch_cent"])
                        if len(match) else float("nan"))
            out.append((int(n["bar_number"]), int(n["note_index"]),
                        float(n["start_s"]), float(n["end_s"]), ref_cent))
        return out

    audio_cache: dict[tuple[str, str], tuple[np.ndarray, int, float]] = {}
    for rec in recordings:
        for seg in VOICE_SEGMENTS:
            srow = segments[(segments["recording_id"] == rec)
                            & (segments["segment_id"] == seg)].iloc[0]
            start = max(0.0, float(srow["start_s"]) - PAD_S)
            dur = float(srow["end_s"]) - start + PAD_S
            y, sr = librosa.load(str(audio_paths[rec]), sr=config.SR_PYIN,
                                 mono=True, offset=start, duration=dur)
            audio_cache[(rec, seg)] = (y, sr, start)
    print(f"audio cached: {len(audio_cache)} (recording, segment) pairs",
          flush=True)

    windows = {(rec, seg): note_windows_for(rec, seg)
               for rec in recordings for seg in VOICE_SEGMENTS}

    seg_rows_out = []
    grid_rows_out = []
    flips = []

    def run_config(label: str, frame: int, hop: int, window_fn) -> None:
        per_rec = {rec: {"off": [], "rho": []} for rec in recordings}
        for rec in recordings:
            for seg in VOICE_SEGMENTS:
                y, sr, load_start = audio_cache[(rec, seg)]
                nw = [(b, i, *window_fn(s, e, k), r)
                      for k, (b, i, s, e, r) in enumerate(windows[(rec, seg)])]
                m = analyse_segment_windows(y, sr, load_start, nw, frame, hop)
                per_rec[rec]["off"].append(m.register_offset_cent)
                per_rec[rec]["rho"].append(m.contour_correlation)
                seg_rows_out.append({
                    "config": label, "recording_id": rec, "segment_id": seg,
                    "n_kept": m.n_notes_used,
                    "offset_cent": (f"{m.register_offset_cent:.3f}"
                                    if not math.isnan(m.register_offset_cent)
                                    else ""),
                    "range_compression": (f"{m.range_compression:.4f}"
                                          if not math.isnan(m.range_compression)
                                          else ""),
                    "contour_correlation": (f"{m.contour_correlation:.4f}"
                                            if not math.isnan(m.contour_correlation)
                                            else ""),
                })
        for rec in recordings:
            off_med = median(per_rec[rec]["off"])
            c_std = std0(per_rec[rec]["rho"])
            typ = classify(c_std, abs(off_med))
            flip = typ != published_type[rec]
            if flip:
                flips.append((label, rec, published_type[rec], typ))
            grid_rows_out.append({
                "config": label, "recording_id": rec,
                "offset_median_cent": f"{off_med:.1f}",
                "contour_std": f"{c_std:.4f}" if not math.isnan(c_std) else "",
                "classified_type": typ,
                "published_type": published_type[rec],
                "flip": "FLIP" if flip else "stable",
            })
        n_flip = sum(1 for g in grid_rows_out
                     if g["config"] == label and g["flip"] == "FLIP")
        print(f"{label:>22s}: flips {n_flip}/{len(recordings)}", flush=True)

    def ident(s: float, e: float, k: int) -> tuple[float, float]:
        return (s, e)

    print("=== part 1: pYIN frame x hop grid ===", flush=True)
    for frame in FRAME_GRID:
        for hop in HOP_GRID:
            run_config(f"frame{frame}-hop{hop}", frame, hop, ident)

    print("=== part 2: onset perturbation (baseline pYIN params) ===", flush=True)
    for label, shift in SHIFT_CONFIGS:
        run_config(label, config.FRAME_LENGTH, config.HOP_LENGTH,
                   lambda s, e, k, sh=shift: (s + sh, e + sh))
    for label, seed in JITTER_CONFIGS:
        rng = np.random.default_rng(seed)
        # One independent uniform draw per note window; call order is
        # deterministic (recording -> segment -> note).
        jit_cache: dict[tuple, float] = {}

        def jitter_fn(s, e, k, rng=rng, cache=jit_cache):
            key = (round(s, 6), round(e, 6), k)
            if key not in cache:
                cache[key] = float(rng.uniform(-JITTER_HALF_WIDTH_S,
                                               JITTER_HALF_WIDTH_S))
            d = cache[key]
            return (s + d, e + d)

        run_config(label, config.FRAME_LENGTH, config.HOP_LENGTH, jitter_fn)

    out1 = OUT / "pyin_perturbation_grid.csv"
    with out1.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(grid_rows_out[0].keys()))
        w.writeheader()
        w.writerows(grid_rows_out)
    out2 = OUT / "pyin_perturbation_segments.csv"
    with out2.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(seg_rows_out[0].keys()))
        w.writeheader()
        w.writerows(seg_rows_out)

    baseline_label = f"frame{config.FRAME_LENGTH}-hop{config.HOP_LENGTH}"
    baseline_flips = [g for g in grid_rows_out
                      if g["config"] == baseline_label and g["flip"] == "FLIP"]
    print("\n=== summary ===")
    print(f"analysed recordings: {len(recordings)}/{len(RECORDINGS)}")
    print(f"sanity gate (baseline {baseline_label} == published): "
          + ("OK" if not baseline_flips else f"FAIL {baseline_flips}"))
    n_configs = (len(FRAME_GRID) * len(HOP_GRID)
                 + len(SHIFT_CONFIGS) + len(JITTER_CONFIGS))
    print(f"total flips: {len(flips)} across {n_configs} configs "
          f"x {len(recordings)} recordings")
    for f_ in flips:
        print("  FLIP:", f_)
    print(f"wrote {out1}")
    print(f"wrote {out2}")


if __name__ == "__main__":
    main()
