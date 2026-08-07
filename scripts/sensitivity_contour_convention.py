#!/usr/bin/env python3
"""Sensitivity of the contour axis to the interval convention.

The paper computes ``contour_correlation`` as the Spearman rho of adjacent
intervals over the *kept* notes (``is_pyin_unreliable == False``): when a
note is filtered out, the interval is formed between its kept neighbours,
i.e. it *bridges* the gap. This script recomputes the contour axis under a
stricter alternative convention -- only pairs of notes that are adjacent in
the segment's note sequence and both kept form an interval; a filtered-out
note removes both the interval into it and out of it, and no bridging
interval is created -- and re-runs the three-type classification.

Input:  results/note_errors_all_segments.csv  (per-note diagnostics,
        rows with source == "demucs_vocals")
        results/segment_metrics.csv           (published values; sanity gate)
Output: results/sensitivity/
  - contour_convention.csv          ... per-segment rho under both conventions
  - contour_convention_summary.csv  ... per-recording sigma_contour + type

Sanity gate: the re-implementation of the published (bridging) convention
must reproduce results/segment_metrics.csv exactly (20/20 segments).

Note: ``note_index`` restarts within each bar, so score order is
(bar_number, note_index), not note_index alone.

Aggregation and classification follow the companion paper (see
scripts/sensitivity_e1.py). Spearman rho is implemented as Pearson over
average ranks (equivalent to scipy.stats.spearmanr).

Dependencies: standard library only (csv, math).
Run: python scripts/sensitivity_contour_convention.py
"""
from __future__ import annotations

import csv
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOTE_ERRORS_CSV = ROOT / "results/note_errors_all_segments.csv"
PUBLISHED_SEGMENT_METRICS = ROOT / "results/segment_metrics.csv"
OUT = ROOT / "results/sensitivity"
OUT.mkdir(parents=True, exist_ok=True)

RECORDINGS = ["ath-1973", "hul-2012", "bou-1961", "bou-1977", "her-1991"]
VOICE_SEGMENTS = ["seg_p07_m5", "seg_p07_m8", "seg_p07_m13", "seg_p07_m18b6_m19b5"]

# Classification thresholds (same as the paper / sensitivity_e1.py)
THRESHOLD_CONTOUR_STD = 0.3
THRESHOLD_OFFSET_ABS = 400


def _f(s: str) -> float:
    return float(s) if (s or "").strip() else float("nan")


def _ranks(xs: list[float]) -> list[float]:
    """Average ranks (ties averaged); matches scipy rankdata(method='average')."""
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    ranks = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        avg = (i + j) / 2 + 1  # 1-based average rank
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def _pearson(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    if sxx <= 0 or syy <= 0:
        return float("nan")
    return sxy / math.sqrt(sxx * syy)


def spearman(xs: list[float], ys: list[float]) -> float:
    if len(xs) < 2:
        return float("nan")
    return _pearson(_ranks(xs), _ranks(ys))


def std0(xs: list[float]) -> float:
    xs = [x for x in xs if not math.isnan(x)]
    if len(xs) < 2:
        return float("nan")
    m = sum(xs) / len(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / len(xs))  # population std


def median(xs: list[float]) -> float:
    xs = sorted(x for x in xs if not math.isnan(x))
    if not xs:
        return float("nan")
    n = len(xs)
    mid = n // 2
    return xs[mid] if n % 2 else (xs[mid - 1] + xs[mid]) / 2


def classify(contour_std: float, offset_abs: float) -> str:
    if not math.isnan(contour_std) and contour_std > THRESHOLD_CONTOUR_STD:
        return "dynamic"
    if not math.isnan(offset_abs) and offset_abs > THRESHOLD_OFFSET_ABS:
        return "directed-recitation"
    return "score-faithful"


def main() -> None:
    with NOTE_ERRORS_CSV.open(encoding="utf-8", newline="") as f:
        raw = list(csv.DictReader(f))
    notes: dict[tuple[str, str], list[dict]] = {}
    for r in raw:
        if r["source"] != "demucs_vocals" or r["segment_id"] not in VOICE_SEGMENTS:
            continue
        if r["recording_id"] not in RECORDINGS:
            continue
        notes.setdefault((r["recording_id"], r["segment_id"]), []).append({
            "bar_number": int(r["bar_number"]),
            "note_index": int(r["note_index"]),  # restarts within each bar
            "ref": _f(r["ref_pitch_cent"]),
            "est": _f(r["est_cent_median"]),
            "kept": (r["is_pyin_unreliable"].lower() != "true"
                     and not math.isnan(_f(r["est_cent_median"]))
                     and not math.isnan(_f(r["ref_pitch_cent"]))),
        })
    for v in notes.values():
        v.sort(key=lambda n: (n["bar_number"], n["note_index"]))

    with PUBLISHED_SEGMENT_METRICS.open(encoding="utf-8", newline="") as f:
        pub_seg = {(r["recording_id"], r["segment_id"]): r for r in csv.DictReader(f)}

    # Published per-recording |offset| (recomputed from segment metrics at
    # full precision, same aggregation as the paper).
    pub_offset_abs = {
        rec: abs(median([_f(pub_seg[(rec, seg)]["performer_offset_cent"])
                         for seg in VOICE_SEGMENTS if (rec, seg) in pub_seg]))
        for rec in RECORDINGS
    }

    out_rows = []
    sanity_fail = 0
    for (rec, seg), ns in sorted(notes.items()):
        kept = [n for n in ns if n["kept"]]

        # Convention A (published, bridging): diffs over the kept sequence.
        if len(kept) >= 3:
            est_iv_a = [b["est"] - a["est"] for a, b in zip(kept, kept[1:])]
            ref_iv_a = [b["ref"] - a["ref"] for a, b in zip(kept, kept[1:])]
            rho_a = spearman(est_iv_a, ref_iv_a)
        else:
            rho_a = float("nan")

        # Convention B (strict adjacency, no bridging): only consecutive
        # rows of the segment's note sequence with both notes kept.
        est_iv_b, ref_iv_b = [], []
        for a, b in zip(ns, ns[1:]):
            if a["kept"] and b["kept"]:
                est_iv_b.append(b["est"] - a["est"])
                ref_iv_b.append(b["ref"] - a["ref"])
        rho_b = spearman(est_iv_b, ref_iv_b) if len(est_iv_b) >= 2 else float("nan")

        # Sanity gate: convention A must reproduce the published value.
        pub = pub_seg.get((rec, seg))
        pub_rho = _f(pub["contour_correlation"]) if pub else float("nan")
        both_nan = math.isnan(rho_a) and math.isnan(pub_rho)
        ok = both_nan or (not math.isnan(rho_a) and not math.isnan(pub_rho)
                          and abs(rho_a - pub_rho) < 1e-9)
        if not ok:
            sanity_fail += 1

        out_rows.append({
            "recording_id": rec,
            "segment_id": seg,
            "n_notes": len(ns),
            "n_kept": len(kept),
            "n_intervals_bridging": max(len(kept) - 1, 0),
            "n_intervals_strict": len(est_iv_b),
            "rho_bridging": f"{rho_a:.6f}" if not math.isnan(rho_a) else "",
            "rho_strict": f"{rho_b:.6f}" if not math.isnan(rho_b) else "",
            "rho_published": f"{pub_rho:.6f}" if not math.isnan(pub_rho) else "",
            "sanity_bridging_matches_published": "OK" if ok else "MISMATCH",
        })

    print("=== per-segment ===")
    print(f'{"rec":10s} {"seg":22s} {"kept":>4s} {"iv_A":>4s} {"iv_B":>4s} '
          f'{"rho_A":>7s} {"rho_B":>7s} {"sanity":>8s}')
    for r in out_rows:
        print(f'{r["recording_id"]:10s} {r["segment_id"]:22s} {r["n_kept"]:>4d} '
              f'{r["n_intervals_bridging"]:>4d} {r["n_intervals_strict"]:>4d} '
              f'{r["rho_bridging"] or "nan":>7.7s} {r["rho_strict"] or "nan":>7.7s} '
              f'{r["sanity_bridging_matches_published"]:>8s}')

    print("\n=== per-recording (sigma_contour and classification) ===")
    print(f'{"rec":10s} {"sd_A":>6s} {"sd_B":>6s} {"med_A":>6s} {"med_B":>6s} '
          f'{"type_A":>20s} {"type_B":>20s} {"flip":>5s}')
    summary_rows = []
    n_flip = 0
    for rec in RECORDINGS:
        rows = [r for r in out_rows if r["recording_id"] == rec]
        rho_as = [float(r["rho_bridging"]) for r in rows if r["rho_bridging"]]
        rho_bs = [float(r["rho_strict"]) for r in rows if r["rho_strict"]]
        sa, sb = std0(rho_as), std0(rho_bs)
        ma, mb = median(rho_as), median(rho_bs)
        off = pub_offset_abs[rec]
        ta, tb = classify(sa, off), classify(sb, off)
        flip = ta != tb
        n_flip += flip
        summary_rows.append({
            "recording_id": rec,
            "offset_median_abs": f"{off:.1f}",
            "contour_std_bridging": f"{sa:.4f}" if not math.isnan(sa) else "",
            "contour_std_strict": f"{sb:.4f}" if not math.isnan(sb) else "",
            "contour_median_bridging": f"{ma:.4f}" if not math.isnan(ma) else "",
            "contour_median_strict": f"{mb:.4f}" if not math.isnan(mb) else "",
            "type_bridging": ta,
            "type_strict": tb,
            "type_flip": "FLIP" if flip else "stable",
        })
        print(f'{rec:10s} {sa:>6.3f} {sb:>6.3f} {ma:>6.2f} {mb:>6.2f} '
              f'{ta:>20s} {tb:>20s} {"FLIP" if flip else "-":>5s}')

    out_csv = OUT / "contour_convention.csv"
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
        w.writeheader()
        w.writerows(out_rows)
    out_csv2 = OUT / "contour_convention_summary.csv"
    with out_csv2.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        w.writeheader()
        w.writerows(summary_rows)

    print(f"\nsanity gate: convention A matches published segment_metrics = "
          f"{len(out_rows) - sanity_fail}/{len(out_rows)}"
          + ("" if sanity_fail == 0 else "  ** MISMATCH -- do not trust results **"))
    print(f"type flips under the strict convention: {n_flip}/{len(RECORDINGS)}")
    print(f"wrote {out_csv}")
    print(f"wrote {out_csv2}")


if __name__ == "__main__":
    main()
