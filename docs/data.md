# Data

This repository ships three metadata CSVs in [`data/metadata/`](../data/metadata/)
and expects the user to fetch one audio file into [`data/audio/`](../data/audio/)
via [`scripts/fetch_audio.py`](../scripts/fetch_audio.py).

License:

- **Metadata CSVs**: CC BY 4.0
- **Code**: MIT (see [LICENSE](../LICENSE))
- **Audio**: not bundled (see [LEGAL_NOTICE.md](../LEGAL_NOTICE.md))

## 1. The three-layer model

The data is organised in three layers, mirroring the analysis pipeline:

| Layer        | File                       | Granularity                              |
|--------------|----------------------------|------------------------------------------|
| Score        | `score_events.csv`         | one row per notated note (per piece)     |
| Acoustic     | `segments.csv`             | one row per voice segment per recording  |
| Mapping      | `segment_score_map.csv`    | one row per (segment, score event) pair  |

The score layer is recording-independent. The acoustic and mapping
layers are joined by `(recording_id, segment_id)`; the mapping layer
joins to the score layer by `(piece_id, bar_number, note_index)`.

## 2. `score_events.csv`

Notated events of one piece, in score order.

| Column           | Type   | Description                                                                 |
|------------------|--------|-----------------------------------------------------------------------------|
| `piece_id`       | str    | Movement identifier. `"07"` for *Pierrot lunaire* No. 7 ("Der kranke Mond").|
| `bar_number`     | int    | Bar number, starting at 1.                                                  |
| `note_index`     | int    | 1-based index within the bar in score order.                                |
| `ref_pitch_name` | str    | Pitch class with octave (`"C5"`, `"A#4"`, `"G#4"`).                         |
| `ref_pitch_cent` | int    | Pitch in cents above C-1 (so `C5 = 7200`, `A4 = 6900`).                     |
| `duration_qn`    | float  | Duration in quarter-note units (`1` = quarter, `0.5` = eighth).             |
| `notes`          | str    | Free-form annotation (e.g. `"voice=1"` for the voice line).                 |

Primary key: `(piece_id, bar_number, note_index)`.

The shipped CSV covers the *voice* part of *Pierrot lunaire* No. 7,
which is the focus of paper 1.

## 3. `segments.csv`

Hand-annotated voice segments per recording.

| Column         | Type   | Description                                                                                |
|----------------|--------|--------------------------------------------------------------------------------------------|
| `recording_id` | str    | Recording identifier (`"ath-1973"`, `"hul-2012"`, `"bou-1961"`, `"bou-1977"`, `"her-1991"`).|
| `piece_id`     | str    | Joins to `score_events.piece_id`.                                                          |
| `segment_id`   | str    | Stable segment label, e.g. `"seg_p07_m18b6_m19b5"` ("piece 07, m18 beat 6 to m19 beat 5"). |
| `start_s`      | float  | Segment start in seconds (relative to the audio file's start).                             |
| `end_s`        | float  | Segment end in seconds.                                                                    |
| `notes`        | str    | Free-form annotation (often Japanese; describes beat positions and any rounding).          |

Primary key: `(recording_id, segment_id)`.

The shipped CSV covers five recordings × four voice segments of
*Pierrot lunaire* No. 7. The segments are:

- `seg_p07_m5`
- `seg_p07_m8`
- `seg_p07_m13`
- `seg_p07_m18b6_m19b5`

## 4. `segment_score_map.csv`

For each segment, the ordered sequence of score events it covers.

| Column         | Type   | Description                                                                  |
|----------------|--------|------------------------------------------------------------------------------|
| `recording_id` | str    | Joins to `segments.recording_id`.                                            |
| `segment_id`   | str    | Joins to `segments.segment_id`.                                              |
| `bar_number`   | int    | Joins to `score_events.bar_number`.                                          |
| `note_index`   | int    | Joins to `score_events.note_index`.                                          |
| `start_s`      | float  | Per-note start in seconds (computed by `alignment.recompute_times`).         |
| `end_s`        | float  | Per-note end in seconds.                                                     |
| `coverage`     | str    | `"full"` for fully-contained notes, `"partial"` for boundary notes.          |
| `notes`        | str    | Free-form annotation.                                                        |

Primary key: `(recording_id, segment_id, bar_number, note_index)`.

The `start_s` / `end_s` columns are derived: each segment's wall-clock
span is divided across its mapped score events in proportion to their
`duration_qn`. To regenerate them after editing `segments.csv` or
`score_events.csv`:

```python
from sprechstimme_pitch.alignment import recompute_times
import csv

with open("data/metadata/segments.csv") as f:
    segments_rows = list(csv.DictReader(f))
with open("data/metadata/score_events.csv") as f:
    score_rows = list(csv.DictReader(f))
with open("data/metadata/segment_score_map.csv") as f:
    map_rows = list(csv.DictReader(f))

updated = recompute_times(
    segments_rows=segments_rows,
    score_events_rows=score_rows,
    map_rows=map_rows,
)
```

## 5. Audio (not bundled)

Audio is fetched on demand from archive.org by
[`scripts/fetch_audio.py`](../scripts/fetch_audio.py). The default demo
recording is:

- Schoenberg, *Pierrot lunaire* op. 21
- Erika Stiedry-Wagner / cond. Schoenberg
- 1940 (Columbia MM-461), uploader-declared license CC BY-NC-SA 3.0
- archive.org item `SCHONBERGPierrotLunaire-NEWTRANSFER`

Read [LEGAL_NOTICE.md](../LEGAL_NOTICE.md) before running the fetch
script — copyright status varies by jurisdiction.

The audio file lands in `data/audio/` and is excluded from version
control by `.gitignore`. The metadata CSVs are *not* tied to a specific
audio file format; you can substitute any wav / flac / mp3 of the same
recording.

## 6. Recording corpus (paper 1)

Five recordings are covered by the shipped metadata. They span the
song-to-speech spectrum that paper 1 analyses:

| recording_id | Reciter / Conductor                | Year | Position on the spectrum (paper 1)|
|--------------|------------------------------------|------|-----------------------------------|
| `ath-1973`   | Atherton (London Sinfonietta)      | 1973 | balanced                           |
| `hul-2012`   | Hulburt et al.                     | 2012 | balanced                           |
| `bou-1961`   | Boulez (Paris, early)              | 1961 | speech-leaning                     |
| `bou-1977`   | Boulez (Sony / BBC, later)         | 1977 | song-leaning                       |
| `her-1991`   | Heringer / Sinopoli                | 1991 | dynamic (high segment-to-segment variance) |

`bou-1961` vs. `bou-1977` provides a same-conductor before/after
contrast within the corpus.

The Stiedry-Wagner 1940 recording fetched by `fetch_audio.py` is the
**demo target**. It is *not* one of the five paper-1 corpus recordings
— it will appear in paper 2 alongside additional historical recordings.
For demonstration purposes the metadata in this repository can be
applied to it (the score events and segment definitions are identical
for any recording of No. 7); the resulting numerics will not match the
paper-1 corpus values.

## 7. Schema versioning

The current schema is sufficient for paper 1. Forward-compatible
extensions planned for paper 2 (Vorwort fidelity, additional
recordings) will likely add columns to `score_events.csv` (Vorwort
markings) and additional rows to `segments.csv` / `segment_score_map.csv`,
without breaking changes to existing columns.

When the schema does change, this document is the source of truth.
