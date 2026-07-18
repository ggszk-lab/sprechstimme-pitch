# E1: sensitivity of the three-type classification (segment-count dependence, threshold perturbation)

Robustness of the deterministic sequential-threshold classification is verified with (a) leave-one-segment-out re-aggregation (4 -> 3 segments) and (b) a threshold perturbation grid. Only the existing data (5 recordings x 4 voice segments) are used; no additional annotation is required.

## Baseline (all 4 segments, thresholds sigma=0.30 / |offset|=400c)

| recording | offset_med (c) | contour_std | type |
|---|---|---|---|
| ath-1973 | -23 | 0.040 | score-faithful |
| hul-2012 | -30 | 0.054 | score-faithful |
| bou-1961 | -668 | 0.067 | directed-recitation |
| bou-1977 | -25 | 0.050 | score-faithful |
| her-1991 | -320 | 0.637 | dynamic |

## (a) Leave-one-segment-out (20 reclassifications)

The baseline type is retained in **20/20** LOSO reclassifications.

| recording | dropped | offset_med (c) | contour_std | LOSO type | stable |
|---|---|---|---|---|---|
| ath-1973 | m13 | -30.0 | 0.029 | score-faithful | ✓ |
| ath-1973 | m18b6_m19b5 | -15.0 | 0.031 | score-faithful | ✓ |
| ath-1973 | m5 | -15.0 | 0.044 | score-faithful | ✓ |
| ath-1973 | m8 | -30.0 | 0.044 | score-faithful | ✓ |
| hul-2012 | m13 | 0.0 | 0.062 | score-faithful | ✓ |
| hul-2012 | m18b6_m19b5 | 0.0 | 0.061 | score-faithful | ✓ |
| hul-2012 | m5 | -60.0 | 0.034 | score-faithful | ✓ |
| hul-2012 | m8 | -60.0 | 0.042 | score-faithful | ✓ |
| bou-1961 | m13 | -805.0 | 0.076 | directed-recitation | ✓ |
| bou-1961 | m18b6_m19b5 | -530.0 | 0.063 | directed-recitation | ✓ |
| bou-1961 | m5 | -805.0 | 0.021 | directed-recitation | ✓ |
| bou-1961 | m8 | -530.0 | 0.076 | directed-recitation | ✓ |
| bou-1977 | m13 | -10.0 | 0.024 | score-faithful | ✓ |
| bou-1977 | m18b6_m19b5 | -10.0 | 0.055 | score-faithful | ✓ |
| bou-1977 | m5 | -40.0 | 0.044 | score-faithful | ✓ |
| bou-1977 | m8 | -40.0 | 0.058 | score-faithful | ✓ |
| her-1991 | m13 | -290.0 | 0.695 | dynamic | ✓ |
| her-1991 | m18b6_m19b5 | -350.0 | 0.46 | dynamic | ✓ |
| her-1991 | m5 | -290.0 | 0.601 | dynamic | ✓ |
| her-1991 | m8 | -350.0 | 0.624 | dynamic | ✓ |

## (b) Threshold perturbation grid (sigma in {.25,.30,.35} x |offset| in {300,400,500}c)

**9** of 9 cells reproduce the baseline labels for all 5 recordings.

| sigma_thr | offset_thr | ath-1973 | hul-2012 | bou-1961 | bou-1977 | her-1991 | =base |
|---|---|---|---|---|---|---|---|
| 0.25 | 300 | SF | SF | DR | SF | DY | ✓ |
| 0.25 | 400 | SF | SF | DR | SF | DY | ✓ |
| 0.25 | 500 | SF | SF | DR | SF | DY | ✓ |
| 0.30 | 300 | SF | SF | DR | SF | DY | ✓ |
| 0.30 | 400 | SF | SF | DR | SF | DY | ✓ ★ |
| 0.30 | 500 | SF | SF | DR | SF | DY | ✓ |
| 0.35 | 300 | SF | SF | DR | SF | DY | ✓ |
| 0.35 | 400 | SF | SF | DR | SF | DY | ✓ |
| 0.35 | 500 | SF | SF | DR | SF | DY | ✓ |

(SF=score-faithful, DR=directed-recitation, DY=dynamic, ★=baseline cell)

## (c) Combined stability rate (5 LOSO states x 9 grid cells = 45 perturbations / recording)

| recording | baseline | stable / total | rate | alt labels |
|---|---|---|---|---|
| ath-1973 | score-faithful | 45/45 | 1.00 | - |
| hul-2012 | score-faithful | 45/45 | 1.00 | - |
| bou-1961 | directed-recitation | 45/45 | 1.00 | - |
| bou-1977 | score-faithful | 45/45 | 1.00 | - |
| her-1991 | dynamic | 45/45 | 1.00 | - |

## (e) Margin to the decision boundaries

Counters the objection that the grid is simply too narrow to flip anything: how far each recording sits from the baseline thresholds (the metric change required to change its label). **Signs read as headroom to the boundary** (positive = the boundary has not been reached).

| recording | type | offset_med (c) | contour_std | -> sigma boundary (0.30) | -> offset boundary (400c) |
|---|---|---|---|---|---|
| ath-1973 | score-faithful | -22.5 | 0.04 | +0.260 | +378 |
| hul-2012 | score-faithful | -30.0 | 0.054 | +0.246 | +370 |
| bou-1961 | directed-recitation | -667.5 | 0.067 | +0.233 | -268 |
| bou-1977 | score-faithful | -25.0 | 0.05 | +0.250 | +375 |
| her-1991 | dynamic | -320.0 | 0.637 | -0.337 | +80 |

- The three **score-faithful** recordings sit far from both boundaries (about +0.25 on the sigma side, +370 to +378c on the offset side); they are not score-faithful by accident.
- **bou-1961 (directed-recitation)** exceeds the 400c boundary by 268c (|offset|=668c); even its smallest LOSO value (530c) stays well beyond the boundary, so the type is stable.
- **her-1991 (dynamic)** exceeds the 0.30 boundary by 0.337 (contour_std=0.637) and remains dynamic even at sigma=0.35.
