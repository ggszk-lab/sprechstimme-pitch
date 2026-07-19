# Listening log

Note-by-note record of the aural checks behind the companion paper.
All checks were made by the author against the issues listed below
(the paper's Table 1), listening to the original mix and, where
relevant, the Demucs vocals stem; segment boundaries were reviewed as
regions in a Reaper session. Dates are the dates each check was
recorded in the analysis repository's decision log, from which this
file is compiled.

| ID | Reciter | Issue consulted |
|---|---|---|
| ath-1973 | Thomas | Decca 425 626-2 |
| bou-1961 | Pilarczyk | Wergo WER 6778-2 |
| bou-1977 | Minton | Sony SMK 48466 |
| her-1991 | Pousseur | Harmonia Mundi HMA 1951390 |
| hul-2012 | Caiello | Praga PRD/DSD 250 276 |

Note addresses below are `bar.note_index` and join to
[`note_errors_all_segments.csv`](note_errors_all_segments.csv) via
(`recording_id`, `bar_number`, `note_index`); cent errors are relative
to the notated pitch (A4 = 440 Hz).

## 1. Segment-window verification (segment level)

Boundaries of the four voice segments (m5, m8, m13, m18.6--m19.5) and
the flute-only reference window (m10--11) per recording.

| recording | segments | how set | listening check |
|---|---|---|---|
| ath-1973 | m18.6--19.5 | set aurally at pilot stage (apportioning reference for all other recordings) | boundary set by ear; note-level subdivision is duration-weighted and marked provisional in the metadata |
| ath-1973 | m5, m8, m13 | estimated from pYIN F0 pattern matching | verified by listening, 2026-04-26 |
| hul-2012 | m18.6--19.5 | as ath-1973 (pilot) | end point shortened by 0.2 s after re-listening |
| hul-2012 | m5, m8, m13 | estimated from pYIN F0 pattern matching | verified by listening, 2026-04-26 |
| bou-1961 | all 4 + m10--11 | duration-ratio apportionment from ath-1973 (ratio 0.8991) | verified by listening, 2026-04-26 |
| bou-1977 | all 4 + m10--11 | duration-ratio apportionment from ath-1973 (ratio 1.0147) | verified by listening, 2026-04-26 |
| her-1991 | all 4 + m10--11 | duration-ratio apportionment from ath-1973 (ratio 1.2101) | verified by listening, 2026-04-26 |

The m10--11 flute-only window (used only for the leakage measurement,
not for pitch metrics) is run at provisional boundary values by design:
what matters is that no voice sounds inside it, not that it coincides
with the barlines (see the analysis decision of 2026-04-26).

Demo recording outside the paper corpus: for sch-1940-sti
(Stiedry-Wagner) the four voice segments were listening-verified
2026-05-17; its m10--11 window is unverified.

## 2. Note-level checks with recorded verdicts

### hul-2012, m8.2 — C♯5 ("mich"), estimated ≈ 1220 cents low → excluded as subharmonic lock

Flagged by the subharmonic criterion (`oct_1`). By ear the pitch is
**not** taken an octave down; the syllable sits in the dense consonant
cluster of "bannt mich". pYIN nevertheless tracks tightly
(voiced ratio 0.92, IQR 50 cents) one octave below the notated
pitch — the signature of a first-subharmonic lock, not of consonant
noise. Verdict: tracking error, excluded. (Recorded 2026-04-26;
this note alone had inflated the segment's mean absolute error from
about 30 to about 208 cents.)

### hul-2012, m19.3 — G♯4, sung ≈ 770 cents low → verified intentional, kept

Not flagged (770 cents matches no subharmonic within the ±50-cent
window). By ear this is clearly an **intentional downward Sprechstimme
deflection**: the realized pitch itself is low, and pYIN tracks it
correctly (voiced ratio 1.0, IQR 50 cents). Verdict: genuine performer
deviation, kept. This case fixed the design rule that no upper cut on
|error| is applied — such a cut would delete exactly the deviations
the axes are meant to observe. (Recorded 2026-04-26.)

### her-1991, m19.6--19.7 — inverted contour (ρ = −0.50 at m18.6--m19.5) → verified performer action

Aural check of the segment with negative contour correlation: Pousseur
takes the notated G♯4 (m19.6) down an octave and keeps the following
C♯4 (m19.7) in the same low register, so the realized line **rises**
where the notated line falls. Verdict: a deliberate re-composition of
the phrase's direction, not a tracking artifact; the kept notes stand.
(Recorded 2026-04-26. Only 4 notes / 3 interval pairs survive the
filter in this segment; the small-n caveat is discussed in the paper.)

## 3. Reliability-filter flag inventory (15 of 120 notes, Demucs vocals)

All notes flagged by the reliability filter (voiced ratio < 0.5, or
within-note F0 IQR > 500 cents, or subharmonic lock within ±50 cents of
±1200/±2400/±700). Reasons come from
[`note_errors_all_segments.csv`](note_errors_all_segments.csv);
the filter is an operational definition on acoustic symptoms, and the
voiced/IQR criteria need no aural adjudication (they flag the absence
of a stable pitch, not a wrong one). Notes flagged by the
score-referencing subharmonic criterion are the ones where listening
matters (could the "lock" be a genuine octave/fifth deviation?);
their verdicts are given below.

| recording | note | pitch | error (c) | reason | listening note |
|---|---|---|---|---|---|
| hul-2012 | m5.6 | D4 | +50 | iqr_high | — (no stable pitch to adjudicate) |
| hul-2012 | m8.2 | C♯5 | −1220 | subharmonic (oct_1) | **checked — lock, excluded** (Section 2) |
| hul-2012 | m8.3 | C5 | −10 | iqr_high | — |
| hul-2012 | m19.2 | B4 | −60 | iqr_high | — |
| bou-1961 | m5.4 | G♯4 | −700 | subharmonic (fifth_down) | **checked — sung low** (see below) |
| bou-1961 | m8.1 | C5 | −720 | subharmonic (fifth_down) | **checked — sung low** (see below) |
| bou-1961 | m8.2 | C♯5 | −680 | subharmonic (fifth_down) | **checked — sung low** (see below) |
| bou-1961 | m8.3 | C5 | −745 | subharmonic (fifth_down) | **checked — sung low** (see below) |
| bou-1961 | m19.4 | C5 | −680 | subharmonic (fifth_down) | **checked — sung low** (see below) |
| her-1991 | m5.5 | B4 | −540 | iqr_high | — |
| her-1991 | m8.1 | C5 | −620 | iqr_high | — |
| her-1991 | m8.2 | C♯5 | (no estimate) | voiced_low | — |
| her-1991 | m19.2 | B4 | −580 | iqr_high | — |
| her-1991 | m19.3 | G♯4 | +380 | voiced_low, iqr_high | — |
| her-1991 | m19.5 | B4 | −1480 | iqr_high | — |

**bou-1961 fifth-down flags (author check, 2026-07-19, note-level
Reaper regions against the Wergo issue):** at all five flagged notes
the voice is audibly *low* — the delivery sits in the same low region
as the estimates, consistent with the recording's overall offset of
−668 cents. The exact pitch is hard to discern in places (low
chest-voice recitation, 1961 source), so a cent-level confirmation of
the estimates is not claimed. Verdict: these are **not** confirmed
tracking locks; the score-referencing criterion here conservatively
excludes plausibly genuine low pitches. The exclusions are retained by
design (the filter is an operational definition), and they do not
affect the results: retaining the notes would only reinforce the
measured offset, and the classification is stable across the filter
grid (`sensitivity/filter_grid_types.csv`). Independent of the
per-note verdicts, the bou-1961 note estimates reproduce the notated
direction profile (on m5, all six note medians — including the flagged
G#4 — follow down-up-up-up-down, with per-note voiced ratios of
0.86–1.00 and within-note IQRs of 40–360 cents), which a stable lock
or flute leakage would not produce.

## 4. Known gaps

- her-1991 m13 (contour correlation 0.00) has not been individually
  listening-checked; the dynamic classification does not depend on it.
- The note-level subdivision of the ath-1973 / hul-2012 pilot segment
  (m18.6--19.5) is duration-weighted and marked provisional in the
  metadata; segment boundaries themselves were set by ear.
