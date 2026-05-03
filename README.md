# sprechstimme-pitch

A reference implementation for quantitative analysis of *Sprechstimme*
(speech-song) in Schoenberg's *Pierrot lunaire* op. 21 (No. 7),
based on pitch tracking of audio recordings.

The framework decomposes a performer's deviation from the score into
three axes:

- **register** (offset) — overall pitch shift relative to the score
- **range** (compression) — compression / expansion of pitch span
- **contour** (direction) — score-informed Spearman correlation of pitch shape

> **Status**: Pre-release. The repository is private until the companion
> paper is accepted. Please contact the author before redistributing.

[日本語版 README](README.ja.md)

## Try it on Colab (5 min)

<!-- TODO: Add Colab badge after public release -->
Open `notebooks/01_quickstart.ipynb` on Google Colab and *Run All*.

## Run locally

```bash
git clone https://github.com/<user>/sprechstimme-pitch.git
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

<!-- TODO: Add DOI and BibTeX after acceptance -->

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
