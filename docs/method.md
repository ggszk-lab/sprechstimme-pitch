# Method

This document describes the analysis pipeline used by `sprechstimme_pitch`,
the rationale for each design choice, and pointers to the implementation.

For a high-level introduction see [README.md](../README.md);
for the dataset itself see [data.md](data.md).

## 1. Pipeline overview

```
Score (MusicXML)                        Recording (.wav / .mp3 / .flac)
   |                                       |
   |  manual transcription / OMR           |  manual segment annotation
   v                                       v
score_events.csv                       segments.csv
   |                                       |
   |       segment_score_map.csv           |
   |       (per-note time windows)         |
   +------------------+--------------------+
                      |
                      v
            sprechstimme_pitch.alignment.recompute_times
            (duration-weighted division of segment time)
                      |
                      v
            sprechstimme_pitch.pitch.track_pitch
            (librosa.pyin -> per-frame f0_hz, voiced_flag)
                      |
                      v
            per-note diagnostics
              note_voiced_ratio, note_f0_iqr_cent
              classify_pitch_class_error, is_pyin_unreliable
                      |
                      v
            sprechstimme_pitch.metrics.compute_three_axis_metrics
              register_offset_cent, range_compression, contour_correlation
                      |
                      v
            aggregate_metrics      ->     classify_performance
            (per-recording)               (score-faithful / directed-recitation / dynamic)
                      |
                      v
            sprechstimme_pitch.plotting.*
            (radar / PCA biplot / decision flow)
```

`notebooks/01_quickstart.ipynb` walks through this pipeline end-to-end
on one segment.

## 2. Three-axis decomposition

The deviation between a performer's pitch and the score is decomposed
into three independent axes, each of which captures a different
musical dimension of the speech-song spectrum.

### register (offset)

Overall pitch shift relative to the score, in cents.

```
register_offset_cent = median(est - score)   # over reliable notes
```

Interpretation: how much higher or lower the performer is, taken as a
whole. A speech-leaning performer often centers far above or below the
notated tessitura.

### range (compression)

Ratio of the pitch span actually used by the performer to the span
notated in the score.

```
range_compression = std(est) / std(score)    # population std, ddof=0
```

Values:

- ≈ 1.0 — the performer uses the same pitch range as the score
- < 1.0 — flattening / monotone delivery
- > 1.0 — exaggerated melodic contour

The implementation requires at least `min_notes` reliable notes
(default `3`) and a non-zero score variance; otherwise it returns NaN.

### contour (direction)

Adherence to the score's pitch shape.

```
contour_correlation = spearmanr(diff(est), diff(score))   # adjacent intervals
```

Values:

- ≈ 1.0 — every interval moves in the direction the score asks for
- 0 — independent of the score
- ≈ -1.0 — systematically opposite to the score

We use `np.diff` (adjacent pitch differences) rather than the raw
sequence so the metric is invariant to register and range — those
dimensions are captured by the other two axes.

A zero-variance guard returns NaN when either side has no interval
variation (for example, all-equal score intervals on which Spearman is
undefined).

### Per-recording aggregation

For type classification we aggregate the per-segment metrics across all
voice segments of one recording:

- `register_offset_cent`        — median across segments
- `range_compression`           — median across segments
- `contour_correlation_median`  — median across segments
- `contour_correlation_std`     — std across segments (the dynamic axis)

`metrics.aggregate_metrics` performs this rollup; missing per-segment
values are skipped via nanmedian / nanstd.

## 3. Performance type classification

A recording is classified into one of three types using a deterministic
decision flow (see `metrics.classify_performance`):

```
contour_std > 0.3 ?                 -> dynamic
otherwise, |offset| > 400 cents ?   -> directed-recitation
otherwise                            -> score-faithful
```

Both thresholds are tuneable function arguments
(`contour_std_threshold`, `offset_abs_threshold_cent`). The defaults are
calibrated against the five-recording paper-1 corpus and may need to be
revisited when extending the analysis to additional recordings.

The decision order matters: a recording with both a large register
offset and high contour variability is labeled `dynamic` rather than
`directed-recitation`, because variability across segments is the more
diagnostic signal of an exploratory / shifting interpretation.

## 4. pYIN reliability filtering (issue #12 spec)

Pitch tracking with pYIN is reliable for sustained voiced tones but
not for whispered, breathy, or rapidly modulated notes that are common
in Sprechstimme. We filter unreliable notes *before* computing the
three-axis metrics, with the explicit goal of keeping the performer's
musical deviation while removing the tracker's locking errors.

A note is flagged as unreliable when **any** of these hold:

| Condition           | Default threshold | Reason tag             |
|---------------------|-------------------|------------------------|
| `voiced_ratio < t`  | `t = 0.5`         | `voiced_low`           |
| `f0_iqr_cent > t`   | `t = 500`         | `iqr_high`             |
| pitch-class error   | `tol = 50` cent   | `pitch_class_<oct_1\|oct_2\|fifth_down\|fifth_up>` |
| `voiced_ratio` NaN  | —                 | `no_estimate`          |

The pitch-class error categorises a per-note error as a typical pYIN
locking artefact:

- `oct_1`      — `|err| ≈ 1200 ± tol` (octave error)
- `oct_2`      — `|err| ≈ 2400 ± tol` (two-octave error)
- `fifth_down` — `err ≈ -700 ± tol`   (fifth subharmonic)
- `fifth_up`   — `err ≈ +700 ± tol`
- `within`     — none of the above

Crucially we do **not** filter notes solely by absolute error magnitude.
A 770-cent deviation that does not match any subharmonic is interpreted
as the performer's intentional speech-like delivery and kept for the
three-axis computation.

`is_pyin_unreliable` returns `(flag, reasons)` where `reasons` is a
comma-separated string drawn from the tags above; the empty string
means reliable. This makes per-corpus filter audits cheap.

## 5. Segment-to-score alignment

`segment_score_map.csv` lists, for each `(recording_id, segment_id)`
pair, the score events covered by that segment in performance order.
The wall-clock time stamps for each note are derived from a simple
duration-weighted division of the segment's total span:

```
note_span_s = segment_span_s * (note.duration_qn / sum(duration_qn))
```

This is implemented in `alignment.recompute_times`. It is intentionally
lightweight for the pilot corpus; a fuller metrical alignment is out of
scope for paper 1.

The fields `start_s` / `end_s` for the *segment* are annotated by hand
in `segments.csv`; the per-note `start_s` / `end_s` in
`segment_score_map.csv` are then computed from those segment boundaries
plus the score's `duration_qn`.

## 6. Implementation map

| Pipeline step        | Module                              | Public entry point                    |
|----------------------|-------------------------------------|---------------------------------------|
| Pitch tracking       | `sprechstimme_pitch.pitch`          | `track_pitch`                         |
| Per-note diagnostics | `sprechstimme_pitch.pitch`          | `note_voiced_ratio`, `note_f0_iqr_cent` |
| Reliability flag     | `sprechstimme_pitch.pitch`          | `classify_pitch_class_error`, `is_pyin_unreliable` |
| Time alignment       | `sprechstimme_pitch.alignment`      | `recompute_times`                     |
| Three-axis metrics   | `sprechstimme_pitch.metrics`        | `compute_three_axis_metrics`          |
| Aggregation          | `sprechstimme_pitch.metrics`        | `aggregate_metrics`                   |
| Classification       | `sprechstimme_pitch.metrics`        | `classify_performance`                |
| Visualization        | `sprechstimme_pitch.plotting`       | `plot_radar_chart`, `plot_pca_biplot`, `plot_type_classification_flow` |

All names are also re-exported at the package top level
(`from sprechstimme_pitch import classify_performance` etc.).

## 7. Reproducibility scope

This repository reproduces the *measurement and classification* layer
of paper 1. Specifically:

- Given identical input audio, identical metadata CSVs, and the same
  pYIN parameters, the per-note pitch estimates are deterministic up to
  floating-point arithmetic.
- The reliability filter, three-axis metrics, aggregation, and type
  classification are pure functions and bit-reproducible across machines.

What this repository **does not** reproduce:

- The original audio recording itself (commercial recordings cannot be
  redistributed; see [LEGAL_NOTICE.md](../LEGAL_NOTICE.md)).
- Manual annotation of segment boundaries (the result is shipped as
  `segments.csv`, but the upstream listening / decision process is not
  in scope).
- Score transcription from the printed parts (shipped as
  `score_events.csv`).

## 8. Known limitations

- **Five-recording corpus**: the type-classification thresholds and
  visualization color/marker maps in `plotting.py` are tuned for the
  paper-1 corpus. Add new recordings carefully and revisit thresholds.
- **Single-piece pipeline**: `piece_id` columns exist in every CSV and
  the code does not hard-code the value, but in practice only
  *Pierrot lunaire* No. 7 is covered. Other movements would need their
  own `score_events.csv` and `segments.csv`.
- **No metrical alignment**: duration-weighted division is a coarse
  approximation that breaks down for heavily rubato passages. For the
  voice segments in this corpus the resulting per-note windows are
  acceptable but not metrically precise.
- **No portamento detection**: continuity / portamento metrics are
  outside paper 1's scope and are deferred to paper 2.
