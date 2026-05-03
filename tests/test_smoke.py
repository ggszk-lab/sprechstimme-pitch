"""Smoke tests that run without audio files (CI-safe)."""

import sprechstimme_pitch


def test_package_imports() -> None:
    assert sprechstimme_pitch.__version__
