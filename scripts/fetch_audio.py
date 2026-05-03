"""Fetch the demo audio recording from archive.org.

This repository does not redistribute audio. Running this script downloads
the Stiedry-Wagner 1940 recording of Schoenberg's Pierrot lunaire op.21
from archive.org on the user's behalf.

LEGAL NOTICE
------------
- EU / Japan: the recording is in the public domain (neighboring rights
  expired in 2011).
- United States: the recording remains under copyright until 2041 under
  the Music Modernization Act (17 U.S.C. Sec.1401). Research use may
  qualify for fair use, but this is the user's determination.
- See LEGAL_NOTICE.md for the full statement.

By running this script you confirm that the download and intended use are
permitted in your jurisdiction.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from urllib.request import urlopen

REPO_ROOT = Path(__file__).resolve().parent.parent
AUDIO_DIR = REPO_ROOT / "data" / "audio"

ARCHIVE_ITEM = "SCHONBERGPierrotLunaire-NEWTRANSFER"
ARCHIVE_URL = f"https://archive.org/details/{ARCHIVE_ITEM}"

# Track 07: "Der kranke Mond" (The Sick Moon)
# Available in MP3 and OGG; using MP3 for broader compatibility
TRACK_NO_7_FILENAME: str = "07. Der kranke Mond (The Sick Moon).mp3"


CONFIRMATION_BANNER = """\
================================================================
  sprechstimme-pitch / fetch_audio.py
================================================================
This script will download audio from archive.org:

  Item    : {item}
  Source  : {url}

Legal status of the 1940 Stiedry-Wagner recording:
  - EU / Japan        : public domain (rights expired 2011)
  - United States     : under copyright until 2041 (MMA)
  - Other juridictions: typically public domain; check local law

By proceeding you confirm that this download and your intended use
are permitted under the law of your jurisdiction. The maintainers
of this repository do not redistribute the audio file and provide
no legal warranty.

See LEGAL_NOTICE.md for the full statement.
================================================================
"""


def confirm() -> bool:
    print(CONFIRMATION_BANNER.format(item=ARCHIVE_ITEM, url=ARCHIVE_URL))
    reply = input("Proceed with download? [y/N] ").strip().lower()
    return reply in {"y", "yes"}


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"  -> {dest}")
    with urlopen(url) as response, dest.open("wb") as f:
        while chunk := response.read(1 << 20):
            f.write(chunk)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip the interactive legal confirmation prompt.",
    )
    args = parser.parse_args()

    if not args.yes and not confirm():
        print("Aborted.")
        return 1

    if TRACK_NO_7_FILENAME is None:
        print(
            "ERROR: track filename has not been pinned in this script yet.\n"
            f"       Please visit {ARCHIVE_URL}, identify the No. 7 track,\n"
            "       and set TRACK_NO_7_FILENAME at the top of this file.",
            file=sys.stderr,
        )
        return 2

    track_url = f"https://archive.org/download/{ARCHIVE_ITEM}/{TRACK_NO_7_FILENAME}"
    dest = AUDIO_DIR / TRACK_NO_7_FILENAME
    download(track_url, dest)
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
