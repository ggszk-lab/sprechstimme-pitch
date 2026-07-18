"""E1 supplement: classification stability over the reliability-filter grid.

From results/note_errors_all_segments.csv (demucs_vocals source), re-runs
filter -> per-segment metrics -> per-recording aggregation -> three-type
classification for a 3x3 grid of voiced / IQR thresholds
(voiced in {0.3, 0.5, 0.7} x IQR in {300, 500, 700} cents; the
subharmonic criterion is held fixed) and checks agreement with the
baseline (voiced 0.5 / IQR 500).

As a by-product, also exports the per-segment direction agreement
(fraction of kept adjacent intervals whose signs match the score):
rho_contour is rank covariation, not sign agreement itself, so the two
are reported separately in the companion paper.

Run:    python scripts/sensitivity_filter_grid.py
Output: results/sensitivity/filter_grid_types.csv
        results/sensitivity/sign_agreement.csv
"""
import csv
import statistics
from collections import defaultdict
from pathlib import Path

from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "results/note_errors_all_segments.csv"
OUT_DIR = ROOT / "results/sensitivity"

SUBH = {"oct_1", "oct_2", "fifth_down", "fifth_up"}
SIGMA_THR, OFFSET_THR = 0.3, 400.0
VOICED_GRID = (0.3, 0.5, 0.7)
IQR_GRID = (300.0, 500.0, 700.0)
BASELINE = (0.5, 500.0)


def load_segments():
    rows = [
        r
        for r in csv.DictReader(open(SRC))
        if r["source"] == "demucs_vocals"
    ]
    segs = defaultdict(list)
    for r in rows:
        segs[(r["recording_id"], r["segment_id"])].append(r)
    for k in segs:
        segs[k].sort(key=lambda r: (int(r["bar_number"]), int(r["note_index"])))
    return segs


def kept_notes(notes, vthr, ithr):
    kept = []
    for r in notes:
        v = float(r["voiced_ratio"]) if r["voiced_ratio"] else float("nan")
        iq = float(r["f0_iqr_cent"]) if r["f0_iqr_cent"] else float("nan")
        bad = (v != v) or v < vthr or iq > ithr or r["pitch_class_error"] in SUBH
        if not bad:
            kept.append((float(r["est_cent_median"]), float(r["ref_pitch_cent"])))
    return kept


def classify_all(segs, vthr, ithr):
    per_rec = defaultdict(lambda: {"off": [], "con": []})
    for (rec, _seg), notes in segs.items():
        kept = kept_notes(notes, vthr, ithr)
        if not kept:
            continue
        per_rec[rec]["off"].append(statistics.median(e - s for e, s in kept))
        if len(kept) >= 3:
            est = [k[0] for k in kept]
            ref = [k[1] for k in kept]
            de = [est[i + 1] - est[i] for i in range(len(est) - 1)]
            dr = [ref[i + 1] - ref[i] for i in range(len(ref) - 1)]
            if statistics.pstdev(de) > 0 and statistics.pstdev(dr) > 0:
                rho, _ = spearmanr(de, dr)
                per_rec[rec]["con"].append(rho)
    types = {}
    for rec, d in per_rec.items():
        off = statistics.median(d["off"])
        sc = statistics.pstdev(d["con"]) if len(d["con"]) > 1 else 0.0
        if sc > SIGMA_THR:
            types[rec] = "dynamic"
        elif abs(off) > OFFSET_THR:
            types[rec] = "directed-recitation"
        else:
            types[rec] = "score-faithful"
    return types


def sign_agreement(segs, vthr, ithr):
    rows = []
    for (rec, seg), notes in sorted(segs.items()):
        kept = kept_notes(notes, vthr, ithr)
        if len(kept) < 3:
            continue
        est = [k[0] for k in kept]
        ref = [k[1] for k in kept]
        de = [est[i + 1] - est[i] for i in range(len(est) - 1)]
        dr = [ref[i + 1] - ref[i] for i in range(len(ref) - 1)]

        def sgn(x):
            return 0 if abs(x) < 1e-9 else (1 if x > 0 else -1)

        agree = sum(1 for a, b in zip(de, dr) if sgn(a) == sgn(b))
        rows.append(
            {
                "recording_id": rec,
                "segment_id": seg,
                "n_pairs": len(de),
                "n_sign_agree": agree,
                "sign_agreement": round(agree / len(de), 3),
            }
        )
    return rows


def main():
    segs = load_segments()
    base = classify_all(segs, *BASELINE)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(OUT_DIR / "filter_grid_types.csv", "w", newline="") as f:
        w = csv.writer(f)
        recs = sorted(base)
        w.writerow(["voiced_threshold", "iqr_threshold_cent", *recs, "same_as_baseline"])
        all_same = True
        for v in VOICED_GRID:
            for i in IQR_GRID:
                t = classify_all(segs, v, i)
                same = t == base
                all_same &= same
                w.writerow([v, i, *[t.get(r, "") for r in recs], same])
                print(f"voiced>{v} iqr>{i}: {'SAME' if same else t}")
        print("ALL CELLS STABLE:", all_same)

    sa = sign_agreement(segs, *BASELINE)
    with open(OUT_DIR / "sign_agreement.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(sa[0].keys()))
        w.writeheader()
        w.writerows(sa)
    print(f"sign_agreement.csv: {len(sa)} rows")


if __name__ == "__main__":
    main()
