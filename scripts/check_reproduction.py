#!/usr/bin/env python3
"""Check a local notebook run against the released results.

Compares ``outputs/paper1/`` (written by
``notebooks/02_paper_reproduction.ipynb`` on the five-recording corpus)
with the released ``results/`` CSVs.

Hard gates (exit 1 on failure):
  - the performance type of every recording matches
    ``results/classification_summary.csv``
  - per-recording median offset within 10 cents, median range within 0.05
  - the per-note reliability-flag set is identical (same notes flagged)

Soft checks (reported, non-fatal):
  - contour median / std deviations. pYIN frame alignment differs
    marginally between the notebook (per-segment) and the analysis
    pipeline, which can move the contour of dense chromatic segments
    (see the reproduction-accuracy note in the notebook intro).

Run: python scripts/check_reproduction.py
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN_DIR = ROOT / "outputs" / "paper1"
RESULTS = ROOT / "results"

sys.path.insert(0, str(ROOT / "src"))
from sprechstimme_pitch import metrics  # noqa: E402

OFFSET_TOL_CENT = 10.0
RANGE_TOL = 0.05
CONTOUR_MED_TOL = 0.05
CONTOUR_STD_TOL = 0.05


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        sys.exit(
            f"missing {path.relative_to(ROOT)} — run "
            "notebooks/02_paper_reproduction.ipynb on the corpus first"
        )
    with path.open() as f:
        return list(csv.DictReader(f))


def main() -> None:
    run_summary = {r["recording_id"]: r for r in read_csv(RUN_DIR / "recording_summary.csv")}
    run_notes = read_csv(RUN_DIR / "note_errors_all_segments.csv")
    ref_summary = {r["recording_id"]: r for r in read_csv(RESULTS / "classification_summary.csv")}
    ref_notes = [
        r
        for r in read_csv(RESULTS / "note_errors_all_segments.csv")
        if r["source"] == "demucs_vocals"
    ]

    failures: list[str] = []
    warnings: list[str] = []

    # --- per-recording aggregates and classification ---
    missing = sorted(set(ref_summary) - set(run_summary))
    if missing:
        failures.append(f"recordings missing from the run: {missing}")

    print(f"{'recording':10s} {'type run/ref':32s} {'d_off':>7s} {'d_rng':>7s} "
          f"{'d_cmed':>7s} {'d_cstd':>7s}")
    for rec in sorted(set(ref_summary) & set(run_summary)):
        run, ref = run_summary[rec], ref_summary[rec]
        run_type = metrics.classify_performance(
            register_offset_cent=float(run["register_offset_cent"]),
            contour_std=float(run["contour_correlation_std"]),
        )
        d_off = float(run["register_offset_cent"]) - float(ref["offset_med_cent"])
        d_rng = float(run["range_compression"]) - float(ref["range_med"])
        d_cmed = float(run["contour_correlation_median"]) - float(ref["contour_med"])
        d_cstd = float(run["contour_correlation_std"]) - float(ref["contour_std"])
        print(f"{rec:10s} {run_type + ' / ' + ref['classified_type']:32s} "
              f"{d_off:+7.1f} {d_rng:+7.3f} {d_cmed:+7.3f} {d_cstd:+7.3f}")

        if run_type != ref["classified_type"]:
            failures.append(
                f"{rec}: classification {run_type} != {ref['classified_type']}"
            )
        if abs(d_off) > OFFSET_TOL_CENT:
            failures.append(f"{rec}: offset off by {d_off:+.1f}c (> {OFFSET_TOL_CENT}c)")
        if abs(d_rng) > RANGE_TOL:
            failures.append(f"{rec}: range off by {d_rng:+.3f} (> {RANGE_TOL})")
        if abs(d_cmed) > CONTOUR_MED_TOL:
            warnings.append(f"{rec}: contour median off by {d_cmed:+.3f}")
        if abs(d_cstd) > CONTOUR_STD_TOL:
            warnings.append(f"{rec}: contour std off by {d_cstd:+.3f}")

    # --- per-note reliability flags ---
    def key(r: dict) -> tuple:
        return (r["recording_id"], r["segment_id"], int(r["bar_number"]), int(r["note_index"]))

    run_flagged = {key(r) for r in run_notes if r["is_pyin_unreliable"] == "True"}
    ref_flagged = {key(r) for r in ref_notes if r["is_pyin_unreliable"] == "True"}
    print(f"\nflags: run {len(run_flagged)} / ref {len(ref_flagged)}")
    for k in sorted(ref_flagged - run_flagged):
        failures.append(f"flag missing in run: {k}")
    for k in sorted(run_flagged - ref_flagged):
        failures.append(f"extra flag in run: {k}")

    # --- verdict ---
    if warnings:
        print("\nwarnings (non-fatal, see the notebook's reproduction-accuracy note):")
        for w in warnings:
            print(f"  - {w}")
    if failures:
        print("\nFAILURES:")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    print("\nOK: classification, aggregates and flag set reproduce the released results.")


if __name__ == "__main__":
    main()
