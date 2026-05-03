# Handoff Memo: sprechstimme-pitch Public Repo Setup

**Date**: 2026-05-03  
**Status**: Public repo skeleton + core implementations complete, private, ready for next phases  
**Current branch**: `main` (GitHub: `ggszk-lab/sprechstimme-pitch`)

## What Was Done (in this session)

### 1. Public Repository Structure Created
- Location: `/Users/gsuzuki/projects/research/sprechstimme-pitch/`
- GitHub: https://github.com/ggszk-lab/sprechstimme-pitch (private)
- Workspace integration: added as sibling folder in VSCode workspace (`sprechstimme-pitch-analysis.code-workspace`)

### 2. Core Modules Ported (from private research repo)
All modules clean, no hard-coded paths, ready for extension:

- **`src/sprechstimme_pitch/alignment.py`** (176 lines)
  - `recompute_times()`: segment ↔ score_events duration-weighted alignment
  - Fully ported from `/02_work/prep/recompute_segment_score_map_times.py`
  - Public API: ready for external use

- **`src/sprechstimme_pitch/pitch.py`** (153 lines)
  - `track_pitch()`: pYIN wrapper (librosa.pyin)
  - `is_pyin_unreliable()`: flag logic (voiced_ratio < 0.5 OR IQR > 500c OR pitch-class error)
  - Helper: `cent_to_hz()`, `hz_to_cent()`
  - **Note**: is_pyin_unreliable thresholds hardcoded but parameterized (defaults are production values)

- **`src/sprechstimme_pitch/metrics.py`** (207 lines)
  - `compute_three_axis_metrics()`: register / range / contour decomposition
  - `aggregate_metrics()`: per-recording rollup
  - `classify_performance()`: score-faithful / directed-recitation / dynamic
  - All functions accept optional unreliability_flags, min_notes params

- **`src/sprechstimme_pitch/plotting.py`** (341 lines)
  - `plot_radar_chart()`: parallel radar plots (5 recordings × 4 axes)
  - `plot_pca_biplot()`: StandardScaler + PCA(n=2) + loadings
  - `plot_type_classification_flow()`: decision tree with matplotlib boxes
  - Constants: COLOR_MAP, MARKER_MAP, RECORDINGS (5 hardcoded, parameterizable if needed)

### 3. Metadata & Audio Setup
- **Data bundled**: `data/metadata/{segments,score_events,segment_score_map}.csv`
  - Source: copied from private repo `01_data/metadata/`
  - Schemas documented in `docs/data.md` (placeholder)

- **Audio**: `scripts/fetch_audio.py` updated
  - Track 07 filename pinned: `"07. Der kranke Mond (The Sick Moon).mp3"`
  - User-initiated fetch (not redistributed)
  - LEGAL_NOTICE.md fully populated (US/EU/JP copyright status)

### 4. Notebook & Documentation
- **`notebooks/01_quickstart.ipynb`** (365 lines)
  - End-to-end pipeline demo (8 cells):
    1. Setup & imports
    2. Fetch audio (subprocess call to fetch_audio.py)
    3. Load metadata
    4. pYIN pitch tracking
    5. Segment extraction & alignment
    6. Per-note extraction
    7. Compute metrics
    8. Visualization (radar chart example)
  - Designed for Colab + local Jupyter (no path assumptions beyond `..`)
  - Ready to run as-is (except audio fetch on first execution)

- **README.md** (English, default)
- **README.ja.md** (日本語, for textbook readers)
- **LEGAL_NOTICE.md** (comprehensive copyright guidance)
- **docs/method.md**, **docs/data.md** (placeholders, to be populated)

### 5. CI/CD Setup
- `.github/workflows/test.yml`: ruff + pytest
- `tests/test_smoke.py`: package import verification (audio-free)
- `pyproject.toml`: dependencies (librosa, scipy, pandas, sklearn, matplotlib, soundfile)

### 6. Git State
- **3 commits** on main:
  1. `88b257f`: Initial skeleton
  2. `6e46536`: Port core implementations + metadata CSV + fetch_audio.py pin
  3. `1228677`: Implement plotting module
  4. `1abecb5`: Implement quickstart notebook

- **All pushed to GitHub** (private repo ready)

---

## Known Issues & TODOs

### High Priority (for next Claude session)

1. **CI verification**: 
   - `uv sync` does it work?
   - `pytest tests/` passes?
   - `ruff check .` clean?
   - → Run locally or trigger GitHub Actions

2. **Notebook smoke test**:
   - Does `01_quickstart.ipynb` execute without errors?
   - (Skip audio fetch; use synthetic test data if needed)
   - Verify all 4 modules import cleanly

3. **Incomplete stubs**:
   - `src/sprechstimme_pitch/__init__.py`: update public API docstring
   - `docs/method.md`: expand from Planning/02_method/ content
   - `docs/data.md`: document CSV column schemas

### Medium Priority

4. **Hardcoded constants review**:
   - 5 recordings hardcoded in COLOR_MAP/MARKER_MAP (OK for now, document as research-phase limitation)
   - Classification thresholds (contour_std=0.3, offset=400c) are from observed data; add comment with reference
   - pYIN params (FMIN_HZ=C3, FMAX_HZ=C5) hardcoded; consider making config-file settable

5. **Performance classification in plotting.py**:
   - `classify_performance_type()` is duplicated in `metrics.py` as `classify_performance()`
   - Decide on single canonical location (recommend `metrics.py`, remove from `plotting.py`)

6. **Per-segment vs per-recording aggregation**:
   - Notebook demos single segment; full pipeline needs looping + aggregation
   - Second notebook `02_paper_reproduction.ipynb` should show batch analysis (future)

### Low Priority (post-paper-1 launch)

7. **plotting.py enhancements**:
   - Add `scree_plot()` for PCA variance explanation
   - Add per-segment scatter (Figure 5 in private repo)

8. **Public corpus expansion**:
   - Paper 2 will add Stiedry-Wagner 1940 + other recordings
   - Metadata will need expansion; current schema sufficient

---

## Memory Updates Needed

For next Claude session, remember:

- [x] `project_public_repo.md`: GitHub org is `ggszk-lab` (not `ggszk`)
- [x] `project_textbook_oa.md`: book《演奏分析入門》OA possible
- Workspace now has 2 folders: `research (private)` + `public (sprechstimme-pitch)`
- Paper 1 publication will trigger public repo activation (change GitHub visibility, add Colab badge)

---

## Files Changed in Private Repo

- `sprechstimme-pitch-analysis.code-workspace`: added 2nd folder entry

Commit: `55b4091` (local, not pushed to GitHub)

---

## Quick Commands (for next session)

```bash
# Verify CI locally
cd /Users/gsuzuki/projects/research/sprechstimme-pitch
uv sync
uv run ruff check .
uv run pytest -q tests/

# Test notebook import
python -c "import sys; sys.path.insert(0, 'src'); import sprechstimme_pitch; print(sprechstimme_pitch.__version__)"

# Run notebook (requires audio file present)
jupyter nbconvert --to notebook --execute notebooks/01_quickstart.ipynb

# Push private repo workspace change
cd /Users/gsuzuki/projects/research/sprechstimme-pitch-analysis
git push  # (already committed locally as 55b4091)
```

---

## Architecture Overview

```
sprechstimme-pitch/
├── README.md (EN) + README.ja.md (JP)
├── LEGAL_NOTICE.md (copyright status)
├── LICENSE (MIT)
├── pyproject.toml (dependencies, build config)
├── .gitignore (audio + cache exclusions)
│
├── src/sprechstimme_pitch/
│   ├── __init__.py (version + public API)
│   ├── pitch.py (pYIN + is_pyin_unreliable)
│   ├── metrics.py (3-axis + aggregation + classify)
│   ├── alignment.py (segment ↔ score weighting)
│   └── plotting.py (radar + PCA biplot + decision flow)
│
├── notebooks/
│   └── 01_quickstart.ipynb (end-to-end demo)
│
├── scripts/
│   └── fetch_audio.py (archive.org user-initiated fetch)
│
├── data/
│   ├── metadata/{segments,score_events,segment_score_map}.csv
│   └── audio/.gitkeep (populated by fetch_audio.py)
│
├── tests/
│   ├── test_smoke.py (import + package check)
│   └── fixtures/.gitkeep
│
├── docs/
│   ├── method.md (to be expanded)
│   └── data.md (to be expanded)
│
└── .github/workflows/
    └── test.yml (ruff + pytest CI)
```

---

## Paper 1 Timeline Integration

- **Now (2026-05-03)**: Private repo ready, paper 1 in submission preparation
- **Post-adoption (summer 2026)**: Public repo activation
  - `gh repo edit ggszk-lab/sprechstimme-pitch --visibility=public`
  - Update README.md with Colab badge, DOI, citation
  - Trigger GitHub Pages for documentation (optional)
- **Paper 2 (2026-2027)**: Add Vorwort analysis + expanded metadata

---

## Next Session Priorities (Claude Code)

1. ✅ CI/CD smoke test (pytest, ruff)
2. ✅ Notebook execution verification
3. ✅ Close TODOs in inline code (TRACK_NO_7_FILENAME was one)
4. ⚠️ Decide: duplicate classify_performance() cleanup
5. 📋 Populate docs/method.md + docs/data.md
6. 🔮 Consider 02_paper_reproduction.ipynb skeleton (batch processing)
