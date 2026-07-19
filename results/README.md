# Released results

Derived data released with the companion paper (Music Performance
Research submission). Everything here is *output* of the pipeline
described in [docs/method.md](../docs/method.md), computed on the
five-recording paper-1 corpus ([docs/data.md](../docs/data.md) §6);
the *input* metadata live in [`data/metadata/`](../data/metadata/).

Provenance: these files were exported from the (private) analysis
repository and are reproducible from the released code — the
per-note layer via `notebooks/02_paper_reproduction.ipynb`, the
sensitivity layer via the two scripts in [`scripts/`](../scripts/)
(see below). License: CC BY 4.0, same as the metadata CSVs.

## Listening log

[`listening_log.md`](listening_log.md) — note-by-note record of the
aural checks reported in the companion paper: segment-window
verification per recording, the recorded verdicts on flagged and
kept-but-deviating notes, and the full reliability-filter flag
inventory with pointers into the per-note CSV.

## Separation-quality layer

### `flute_leakage_m10_m11.csv`

One row per recording: the separation-quality measurement reported in
the paper (Method, source separation). On the flute-only passage
mm. 10-11 (`seg_p07_m10_m11`), `rms_ratio_vocals_over_orig` is the
ratio of RMS amplitudes between the separated vocals stem and the
original mix — the residual flute leakage (0.5% for ath-1973 and
hul-2012 up to 7.2% for bou-1961). Exported from the (private)
analysis repository like the per-note layer.

## Per-note layer

### `note_errors_all_segments.csv`

One row per (recording, segment, source, note): the per-note pitch
estimates **with exclusion reasons**, i.e. the layer between raw pYIN
frames and the per-segment metrics.

| column | meaning |
|---|---|
| `recording_id`, `segment_id` | join keys to `data/metadata/segments.csv` |
| `source` | `demucs_vocals` (separated vocals stem, used in the paper) or `original` (unseparated mix, robustness comparison) |
| `bar_number`, `note_index` | join keys to `data/metadata/score_events.csv` |
| `ref_pitch_name`, `ref_pitch_cent` | notated pitch and its cent value (A4 = 440 Hz reference) |
| `voiced_ratio` | fraction of pYIN frames voiced within the note window |
| `f0_iqr_cent` | interquartile range of f0 within the note window, cents |
| `est_cent_median` | median estimated pitch of the note, cents |
| `error_cent`, `abs_error_cent` | signed / absolute deviation from `ref_pitch_cent` |
| `pitch_class_error` | `within` or a subharmonic/octave label (`oct_1`, `oct_2`, `fifth_down`, `fifth_up`, …) |
| `is_pyin_unreliable` | reliability-filter verdict (voiced < 0.5 OR IQR > 500c OR subharmonic lock) |
| `unreliable_reasons` | which criteria fired (empty when reliable) |

With the paper's baseline filter, 15 of 120 notes (demucs_vocals,
5 recordings x 24 notes) are flagged unreliable; on the unseparated
`original` source the count rises to 24.

## Per-segment / per-recording layer

### `segment_metrics.csv`

One row per (recording, segment): the three axes at full precision.
Key columns: `performer_offset_cent` (register), `range_compression`
(range), `contour_correlation` (contour, score-informed Spearman rho),
plus `n_notes` / `n_kept` (notes surviving the reliability filter) and
supporting statistics. This file is the input to
`scripts/sensitivity_e1.py`.

### `classification_summary.csv`

One row per recording: aggregated axes (`offset_med_cent`, `range_med`,
`contour_med`, `contour_std`), the resulting `classified_type`
(score-faithful / directed-recitation / dynamic), and the
`classification_basis` string spelling out which thresholds decided it.

## Sensitivity layer (`sensitivity/`)

Robustness checks reported in the companion paper (Section on
sensitivity analysis and the appendix). Regenerate with:

```bash
python scripts/sensitivity_e1.py           # stdlib only
python scripts/sensitivity_filter_grid.py  # needs scipy (installed via uv sync)
```

| file | produced by | content |
|---|---|---|
| `loso_reclassification.csv` | `sensitivity_e1.py` | leave-one-segment-out reclassification (20 cases; all stable) |
| `threshold_grid.csv` | `sensitivity_e1.py` | classification thresholds grid, sigma x offset 3x3 (9/9 match baseline) |
| `stability_summary.csv` | `sensitivity_e1.py` | combined stability rate, 45 perturbations per recording (all 1.00) |
| `boundary_margin.csv` | `sensitivity_e1.py` | headroom of each recording to the decision boundaries |
| `E1_sensitivity_summary.md` | `sensitivity_e1.py` | human-readable summary of the above |
| `filter_grid_types.csv` | `sensitivity_filter_grid.py` | reliability-filter thresholds grid, voiced x IQR 3x3 (all cells reproduce the baseline types) |
| `sign_agreement.csv` | `sensitivity_filter_grid.py` | per-segment direction agreement of kept adjacent intervals (complement to rank-based contour) |
| `pyin_unreliability_sensitivity.csv` | exported from the private analysis repository | flagged-note counts over the same voiced x IQR 3x3 filter grid (n_flagged 13-24 of 120; the paper's "13 to 24" figure) plus MAE summaries |
