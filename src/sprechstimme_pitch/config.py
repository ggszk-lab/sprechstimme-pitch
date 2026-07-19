"""Paper-1 pipeline configuration — the single source of truth.

Every entry point (library defaults, notebooks, scripts, tests) must
import these values instead of repeating the literals, so that a change
here propagates everywhere at once.
"""

SR_PYIN = 22050
"""Sample rate audio is resampled to (mono) before pYIN."""

FMIN_HZ = 130.8
"""pYIN lower bound: C3."""

FMAX_HZ = 1046.5
"""pYIN upper bound: C6 (the movement's voice part tops at D5 = 587 Hz)."""

FRAME_LENGTH = 2048
"""pYIN frame length in samples (~93 ms at 22.05 kHz)."""

HOP_LENGTH = 256
"""pYIN hop length in samples (~11.6 ms at 22.05 kHz)."""
