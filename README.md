# sprechstimme-pitch

A reference implementation for quantitative analysis of *Sprechstimme*
(speech-song) in Schoenberg's *Pierrot lunaire* op. 21 (No. 7),
based on pitch tracking of audio recordings.

The framework decomposes a performer's deviation from the score into
three axes:

- **register** (offset) — overall pitch shift relative to the score
- **range** (compression) — compression / expansion of pitch span
- **contour** (direction) — score-informed Spearman correlation of pitch shape

> **Status**: Released ahead of the submission of the companion paper to
> *Music Performance Research*, whose data-and-code statement points at
> this repository. A companion presentation at the Fall Meeting of the
> Japanese Society for Music Perception and Cognition (JSMPC) is
> scheduled for 31 October--1 November 2026.

[日本語版 README](README.ja.md)

## Try it on Colab (5 min)

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/ggszk-lab/sprechstimme-pitch/blob/main/notebooks/01_quickstart.ipynb)

Open `notebooks/01_quickstart.ipynb` on Google Colab and *Run All*.

## Notebooks

- [`notebooks/01_quickstart.ipynb`](notebooks/01_quickstart.ipynb) —
  end-to-end pipeline on a single voice segment. The shortest path
  from raw audio to the three-axis metrics.
- [`notebooks/02_paper_reproduction.ipynb`](notebooks/02_paper_reproduction.ipynb) —
  batch pipeline over the five-recording corpus: per-segment metrics,
  per-recording aggregation, type classification, and the three core
  paper figures (radar, PCA biplot, decision flow). Recordings whose
  audio is not on disk are skipped, so the notebook works on any
  available subset.

## Released results

[`results/`](results/README.md) ships the derived data behind the
companion paper: per-note pitch estimates with exclusion reasons,
per-segment three-axis metrics, the type-classification summary, the
sensitivity analyses (regenerable via `scripts/sensitivity_e1.py` and
`scripts/sensitivity_filter_grid.py`), and the note-by-note
[listening log](results/listening_log.md).

## Run locally

```bash
git clone https://github.com/ggszk-lab/sprechstimme-pitch.git
cd sprechstimme-pitch
uv sync                                 # install dependencies
python scripts/fetch_audio.py           # fetch audio from archive.org
jupyter lab notebooks/01_quickstart.ipynb
```

## Audio source

This repository **does not bundle audio files**.
`scripts/fetch_audio.py` fetches the Stiedry-Wagner 1940 recording
from archive.org on the user's behalf.

- Recording: Schoenberg, *Pierrot lunaire* op. 21,
  Erika Stiedry-Wagner / cond. Schoenberg, 1940 (Columbia MM-461)
- Source: [archive.org/details/SCHONBERGPierrotLunaire-NEWTRANSFER](https://archive.org/details/SCHONBERGPierrotLunaire-NEWTRANSFER)
- Uploader-declared license: CC BY-NC-SA 3.0

**Important legal note**: in the United States this 1940 recording
remains under copyright until 2041 under the Music Modernization Act.
In the EU and Japan the neighboring rights expired in 2011.
See [LEGAL_NOTICE.md](LEGAL_NOTICE.md) before running the fetch script.

## Citation

The companion journal article is under submission. Until it is
published, please cite this repository directly
(see also [CITATION.cff](CITATION.cff)):

```bibtex
@software{suzuki2026sprechstimmepitch,
  author  = {Suzuki, Gengo},
  title   = {sprechstimme-pitch: quantitative three-axis analysis of
             Sprechstimme pitch in Pierrot lunaire No.~7},
  year    = {2026},
  url     = {https://github.com/ggszk-lab/sprechstimme-pitch},
  version = {0.1.0},
  note    = {Reference implementation and released data for the
             companion paper (under submission)}
}
```

<!-- TODO: replace with the article citation once the MPR paper (or the
     JSMPC Fall 2026 proceedings paper) is published -->

## License

- Code: MIT — see [LICENSE](LICENSE)
- Metadata CSVs: CC BY 4.0
- Audio: not bundled — see [LEGAL_NOTICE.md](LEGAL_NOTICE.md)

## Companion projects

- Research repository (private): full analysis pipeline, decision logs,
  and metadata for all 22 recordings
- Textbook *Introduction to Performance Analysis — Mathematics and Practice
  of Musical Acoustics* (in preparation): Chapter 11 will reuse the
  notebooks in this repository as instructional material
