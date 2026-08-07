#!/usr/bin/env python3
"""Export the PCA reported in the companion paper as CSV artifacts.

Recomputes the 2-component PCA over the four normalized deviation
quantities (the three axes plus sigma_contour) for the five paper-1
recordings, exactly as drawn in the biplot (Figure 2 of the paper /
notebook 02): per-recording aggregates -> four_axes_normalize ->
StandardScaler -> PCA(n_components=2). The displayed loadings are the
component vectors scaled by sqrt(explained variance), matching the
arrows in the biplot; under scikit-learn's conventions at n=5 these
are not bounded by +-1 and are not variable-component correlations
(see the paper, Results, axis non-redundancy).

Input:  results/classification_summary.csv  (per-recording aggregates)
Output: results/pca/
  - pca_explained_variance.csv ... eigenvalue, variance ratio, cumulative per PC
  - pca_loadings.csv           ... raw components and scaled loadings per quantity
  - pca_scores.csv             ... PC1/PC2 coordinates per recording

Dependencies: numpy, scikit-learn (same as the plotting module).
Run: python scripts/export_pca.py
"""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "results/classification_summary.csv"
OUT = ROOT / "results/pca"

AXIS_KEYS = ["abs_offset", "range_dev", "contour_dev", "contour_std"]


def four_axes_normalize(
    offset_med_cent: float, range_med: float, contour_med: float, contour_std: float
) -> list[float]:
    """Same normalization as sprechstimme_pitch.plotting.four_axes_normalize."""
    return [
        abs(offset_med_cent) / 1000.0,
        abs(1.0 - range_med),
        1.0 - contour_med,
        contour_std,
    ]


def main() -> None:
    with SRC.open(newline="") as f:
        rows = list(csv.DictReader(f))

    rec_ids = [r["recording_id"] for r in rows]
    x = np.array(
        [
            four_axes_normalize(
                float(r["offset_med_cent"]),
                float(r["range_med"]),
                float(r["contour_med"]),
                float(r["contour_std"]),
            )
            for r in rows
        ]
    )

    x_std = StandardScaler().fit_transform(x)
    pca = PCA(n_components=2)
    scores = pca.fit_transform(x_std)
    scaled_loadings = pca.components_.T * np.sqrt(pca.explained_variance_)

    OUT.mkdir(parents=True, exist_ok=True)

    with (OUT / "pca_explained_variance.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["component", "eigenvalue", "explained_variance_ratio", "cumulative_ratio"])
        cum = 0.0
        for i in range(2):
            cum += pca.explained_variance_ratio_[i]
            w.writerow(
                [
                    f"PC{i + 1}",
                    f"{pca.explained_variance_[i]:.6f}",
                    f"{pca.explained_variance_ratio_[i]:.6f}",
                    f"{cum:.6f}",
                ]
            )

    with (OUT / "pca_loadings.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "quantity",
                "component_PC1",
                "component_PC2",
                "scaled_loading_PC1",
                "scaled_loading_PC2",
            ]
        )
        for i, key in enumerate(AXIS_KEYS):
            w.writerow(
                [
                    key,
                    f"{pca.components_[0, i]:.6f}",
                    f"{pca.components_[1, i]:.6f}",
                    f"{scaled_loadings[i, 0]:.6f}",
                    f"{scaled_loadings[i, 1]:.6f}",
                ]
            )

    with (OUT / "pca_scores.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["recording_id", "PC1", "PC2"])
        for rid, (pc1, pc2) in zip(rec_ids, scores):
            w.writerow([rid, f"{pc1:.6f}", f"{pc2:.6f}"])

    ratios = pca.explained_variance_ratio_
    print(f"PC1 {ratios[0]:.1%}, PC2 {ratios[1]:.1%}, cumulative {ratios.sum():.1%}")
    for name in ("pca_explained_variance.csv", "pca_loadings.csv", "pca_scores.csv"):
        print(f"Wrote {OUT / name}")


if __name__ == "__main__":
    main()
