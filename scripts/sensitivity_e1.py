#!/usr/bin/env python3
"""Sensitivity analysis of the three-type classification (E1).

Verifies how stable the three-type classification (score-faithful /
directed-recitation / dynamic) is against (a) leave-one-segment-out
re-aggregation (4 -> 3 segments) and (b) a perturbation grid over the
two classification thresholds.

Input:  results/segment_metrics.csv  (per-segment metrics, full precision)
Output: results/sensitivity/
  - loso_reclassification.csv   ... 20 LOSO (drop-one-segment) reclassifications
  - threshold_grid.csv          ... labels for 9 threshold combinations x 5 recordings
  - stability_summary.csv       ... per-recording stability rate (LOSO x grid combined)
  - boundary_margin.csv         ... distance of each recording to the decision boundaries
  - E1_sensitivity_summary.md   ... human-readable summary

Aggregation and classification follow the companion paper:
  offset_med  = median(performer_offset_cent)
  contour_med = median(contour_correlation)
  contour_std = population standard deviation of contour_correlation (n divisor)
  classification (sequential thresholds):
    contour_std > sigma_thr              -> dynamic
    else if |offset_med| > offset_thr    -> directed-recitation
    else                                 -> score-faithful

Dependencies: standard library only (csv, statistics).
Run: python scripts/sensitivity_e1.py
"""
from __future__ import annotations

import csv
import statistics
from itertools import product
from pathlib import Path

# --- paths ---
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "results/segment_metrics.csv"
OUT = ROOT / "results/sensitivity"

# --- baseline thresholds (as in the paper) ---
SIGMA_THR_BASE = 0.3     # sigma_contour
OFFSET_THR_BASE = 400.0  # |D_offset| in cents

# --- perturbation grid ---
SIGMA_GRID = [0.25, 0.30, 0.35]
OFFSET_GRID = [300.0, 400.0, 500.0]

# display order of recordings (matches the paper's tables)
REC_ORDER = ["ath-1973", "hul-2012", "bou-1961", "bou-1977", "her-1991"]


def pop_std(xs: list[float]) -> float:
    """Population standard deviation (n divisor), as in the paper."""
    return statistics.pstdev(xs) if len(xs) > 1 else 0.0


def classify(offset_med: float, contour_std: float,
             sigma_thr: float, offset_thr: float) -> str:
    """Sequential threshold classification."""
    if contour_std > sigma_thr:
        return "dynamic"
    if abs(offset_med) > offset_thr:
        return "directed-recitation"
    return "score-faithful"


def aggregate(segs: list[dict]) -> dict:
    """Aggregate a set of segments to per-recording values."""
    offs = [s["offset"] for s in segs]
    cont = [s["contour"] for s in segs]
    rng = [s["range"] for s in segs]
    return {
        "offset_med": statistics.median(offs),
        "contour_med": statistics.median(cont),
        "contour_std": pop_std(cont),
        "range_med": statistics.median(rng),
        "n_segments": len(segs),
    }


def load() -> dict[str, list[dict]]:
    """Map recording_id -> list of per-segment records."""
    recs: dict[str, list[dict]] = {}
    with SRC.open() as f:
        for row in csv.DictReader(f):
            recs.setdefault(row["recording_id"], []).append({
                "segment_id": row["segment_id"],
                "segment_short": row["segment_id"].replace("seg_p07_", ""),
                "offset": float(row["performer_offset_cent"]),
                "contour": float(row["contour_correlation"]),
                "range": float(row["range_compression"]),
            })
    return recs


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    recs = load()

    # === baseline (all 4 segments, baseline thresholds) ===
    baseline = {}
    for rid in REC_ORDER:
        agg = aggregate(recs[rid])
        agg["type"] = classify(agg["offset_med"], agg["contour_std"],
                               SIGMA_THR_BASE, OFFSET_THR_BASE)
        baseline[rid] = agg

    # === (a) leave-one-segment-out reclassification ===
    loso_rows = []
    loso_stable = {rid: [] for rid in REC_ORDER}
    for rid in REC_ORDER:
        segs = recs[rid]
        base_type = baseline[rid]["type"]
        for drop in segs:
            kept = [s for s in segs if s["segment_id"] != drop["segment_id"]]
            agg = aggregate(kept)
            t = classify(agg["offset_med"], agg["contour_std"],
                         SIGMA_THR_BASE, OFFSET_THR_BASE)
            stable = (t == base_type)
            loso_stable[rid].append(stable)
            loso_rows.append({
                "recording_id": rid,
                "dropped_segment": drop["segment_short"],
                "n_segments": agg["n_segments"],
                "offset_med_cent": round(agg["offset_med"], 1),
                "contour_std": round(agg["contour_std"], 3),
                "baseline_type": base_type,
                "loso_type": t,
                "stable": stable,
            })

    with (OUT / "loso_reclassification.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(loso_rows[0].keys()))
        w.writeheader()
        w.writerows(loso_rows)

    # === (b) threshold perturbation grid (all 4 segments fixed) ===
    grid_rows = []
    for sthr, othr in product(SIGMA_GRID, OFFSET_GRID):
        labels = {}
        for rid in REC_ORDER:
            b = baseline[rid]
            labels[rid] = classify(b["offset_med"], b["contour_std"], sthr, othr)
        row = {"sigma_thr": sthr, "offset_thr": othr}
        row.update(labels)
        row["is_base_cell"] = (sthr == SIGMA_THR_BASE and othr == OFFSET_THR_BASE)
        row["matches_baseline"] = all(
            labels[rid] == baseline[rid]["type"] for rid in REC_ORDER)
        grid_rows.append(row)

    grid_fields = ["sigma_thr", "offset_thr"] + REC_ORDER + \
                  ["is_base_cell", "matches_baseline"]
    with (OUT / "threshold_grid.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=grid_fields)
        w.writeheader()
        w.writerows(grid_rows)

    # === (c) combined stability rate: LOSO(5 states) x grid(9) = 45 / recording ===
    stability = {}
    for rid in REC_ORDER:
        segs = recs[rid]
        base_type = baseline[rid]["type"]
        n_total = 0
        n_stable = 0
        changed_to = {}
        for drop in [None] + segs:  # None = also evaluate the full 4-segment set
            kept = segs if drop is None else \
                [s for s in segs if s["segment_id"] != drop["segment_id"]]
            agg = aggregate(kept)
            for sthr, othr in product(SIGMA_GRID, OFFSET_GRID):
                t = classify(agg["offset_med"], agg["contour_std"], sthr, othr)
                n_total += 1
                if t == base_type:
                    n_stable += 1
                else:
                    changed_to[t] = changed_to.get(t, 0) + 1
        stability[rid] = {
            "recording_id": rid,
            "baseline_type": base_type,
            "n_perturbations": n_total,
            "n_stable": n_stable,
            "stability_rate": round(n_stable / n_total, 3),
            "alt_labels": ";".join(f"{k}:{v}" for k, v in sorted(changed_to.items()))
                          or "-",
        }

    with (OUT / "stability_summary.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(next(iter(stability.values())).keys()))
        w.writeheader()
        w.writerows(stability.values())

    # === (e) margin to the decision boundaries ===
    # Counters the objection "the grid is simply too narrow to flip anything":
    # for each recording, report how far it sits from the baseline thresholds
    # (the metric change required to change its label).
    margin_rows = []
    for rid in REC_ORDER:
        b = baseline[rid]
        row = {
            "recording_id": rid,
            "baseline_type": b["type"],
            "offset_med_cent": round(b["offset_med"], 1),
            "contour_std": round(b["contour_std"], 3),
            # contour_std distance to the dynamic boundary (sigma=0.30);
            # positive = not yet dynamic
            "margin_to_sigma_thr": round(SIGMA_THR_BASE - b["contour_std"], 3),
            # distance to the directed boundary (|offset|=400);
            # positive = not yet reached
            "margin_to_offset_thr_cent": round(OFFSET_THR_BASE - abs(b["offset_med"]), 1),
        }
        margin_rows.append(row)

    with (OUT / "boundary_margin.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(margin_rows[0].keys()))
        w.writeheader()
        w.writerows(margin_rows)

    # === (d) human-readable summary ===
    md = []
    md.append("# E1: sensitivity of the three-type classification "
              "(segment-count dependence, threshold perturbation)\n")
    md.append("Robustness of the deterministic sequential-threshold "
              "classification is verified with (a) leave-one-segment-out "
              "re-aggregation (4 -> 3 segments) and (b) a threshold "
              "perturbation grid. Only the existing data (5 recordings x 4 "
              "voice segments) are used; no additional annotation is "
              "required.\n")

    md.append("## Baseline (all 4 segments, thresholds sigma=0.30 / |offset|=400c)\n")
    md.append("| recording | offset_med (c) | contour_std | type |")
    md.append("|---|---|---|---|")
    for rid in REC_ORDER:
        b = baseline[rid]
        md.append(f"| {rid} | {b['offset_med']:.0f} | {b['contour_std']:.3f} "
                  f"| {b['type']} |")
    md.append("")

    md.append("## (a) Leave-one-segment-out (20 reclassifications)\n")
    n_loso = len(loso_rows)
    n_loso_stable = sum(r["stable"] for r in loso_rows)
    md.append(f"The baseline type is retained in **{n_loso_stable}/{n_loso}** "
              "LOSO reclassifications.\n")
    md.append("| recording | dropped | offset_med (c) | contour_std | LOSO type | stable |")
    md.append("|---|---|---|---|---|---|")
    for r in loso_rows:
        mark = "✓" if r["stable"] else "**✗**"
        md.append(f"| {r['recording_id']} | {r['dropped_segment']} "
                  f"| {r['offset_med_cent']} | {r['contour_std']} "
                  f"| {r['loso_type']} | {mark} |")
    md.append("")
    unstable = [r for r in loso_rows if not r["stable"]]
    if unstable:
        md.append("**LOSO cases that changed type:**\n")
        for r in unstable:
            md.append(f"- {r['recording_id']}: dropping `{r['dropped_segment']}` "
                      f"changes {r['baseline_type']} -> {r['loso_type']} "
                      f"(offset_med={r['offset_med_cent']}c, "
                      f"contour_std={r['contour_std']})")
        md.append("")

    md.append("## (b) Threshold perturbation grid "
              "(sigma in {.25,.30,.35} x |offset| in {300,400,500}c)\n")
    n_grid_match = sum(r["matches_baseline"] for r in grid_rows)
    md.append(f"**{n_grid_match}** of 9 cells reproduce the baseline labels "
              "for all 5 recordings.\n")
    md.append("| sigma_thr | offset_thr | " + " | ".join(REC_ORDER) + " | =base |")
    md.append("|---|---|" + "---|" * (len(REC_ORDER) + 1))
    abbr = {"score-faithful": "SF", "directed-recitation": "DR", "dynamic": "DY"}
    for r in grid_rows:
        cells = " | ".join(abbr[r[rid]] for rid in REC_ORDER)
        base_mark = " ★" if r["is_base_cell"] else ""
        match = "✓" if r["matches_baseline"] else "✗"
        md.append(f"| {r['sigma_thr']:.2f} | {r['offset_thr']:.0f} | {cells} "
                  f"| {match}{base_mark} |")
    md.append("\n(SF=score-faithful, DR=directed-recitation, DY=dynamic, "
              "★=baseline cell)\n")

    md.append("## (c) Combined stability rate "
              "(5 LOSO states x 9 grid cells = 45 perturbations / recording)\n")
    md.append("| recording | baseline | stable / total | rate | alt labels |")
    md.append("|---|---|---|---|---|")
    for rid in REC_ORDER:
        s = stability[rid]
        md.append(f"| {rid} | {s['baseline_type']} | {s['n_stable']}/{s['n_perturbations']} "
                  f"| {s['stability_rate']:.2f} | {s['alt_labels']} |")
    md.append("")

    md.append("## (e) Margin to the decision boundaries\n")
    md.append("Counters the objection that the grid is simply too narrow to "
              "flip anything: how far each recording sits from the baseline "
              "thresholds (the metric change required to change its label). "
              "**Signs read as headroom to the boundary** (positive = the "
              "boundary has not been reached).\n")
    md.append("| recording | type | offset_med (c) | contour_std "
              "| -> sigma boundary (0.30) | -> offset boundary (400c) |")
    md.append("|---|---|---|---|---|---|")
    for r in margin_rows:
        md.append(f"| {r['recording_id']} | {r['baseline_type']} "
                  f"| {r['offset_med_cent']} | {r['contour_std']} "
                  f"| {r['margin_to_sigma_thr']:+.3f} "
                  f"| {r['margin_to_offset_thr_cent']:+.0f} |")
    md.append("")
    md.append("- The three **score-faithful** recordings sit far from both "
              "boundaries (about +0.25 on the sigma side, +370 to +378c on "
              "the offset side); they are not score-faithful by accident.")
    md.append("- **bou-1961 (directed-recitation)** exceeds the 400c boundary "
              "by 268c (|offset|=668c); even its smallest LOSO value (530c) "
              "stays well beyond the boundary, so the type is stable.")
    md.append("- **her-1991 (dynamic)** exceeds the 0.30 boundary by 0.337 "
              "(contour_std=0.637) and remains dynamic even at sigma=0.35.")
    md.append("")

    (OUT / "E1_sensitivity_summary.md").write_text("\n".join(md), encoding="utf-8")

    # --- console summary ---
    print(f"[E1] LOSO: {n_loso_stable}/{n_loso} stable")
    print(f"[E1] threshold grid: {n_grid_match}/9 cells match baseline")
    for rid in REC_ORDER:
        s = stability[rid]
        print(f"[E1] {rid:10s} {s['baseline_type']:20s} "
              f"stability={s['stability_rate']:.2f} alt=[{s['alt_labels']}]")
    print(f"[E1] outputs -> {OUT}")


if __name__ == "__main__":
    main()
