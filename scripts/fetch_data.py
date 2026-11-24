"""Loads the public IDC dataset from a pinned commit into data/idc/.

Verifies every file via SHA-256. On a mismatch the script aborts with exit code 1,
so that a silently changed data basis is noticed.

Source and license (CC BY 4.0): see DATA.md
"""

from __future__ import annotations

import hashlib
import sys
import urllib.request
from pathlib import Path

REPO = "Immunogenicity-Database-Collaborative/IDC-DB"
PINNED_REF = "f5a381206c37585b1fd2f120d9b188c86360534a"
BASE_URL = f"https://raw.githubusercontent.com/{REPO}/{PINNED_REF}"

# File name -> SHA-256 of the content in the pinned commit
FILES: dict[str, str] = {
    "therapeutics.csv": "6641dc2fa89fa4cebe6453658351d7a3e222f26e292a826a19e4b87741ded5d7",
    "clinical_trials.csv": "5b6433c2378cf1e3787253eea4b24eed7eccb2aaf5e932d69516258ad87d4c3f",
    "aggregated_ada_values.csv": "ff8cf45392beffebad5d4b7670285ae6c72abee917a7e478d6d325b0f55a4390",
    "sequences.csv": "115d19b9a28707ed09f92942288cdc4d1f5b211b13cc54e55c947fb99f2d7c31",
    "variables_explained.csv": "4905933aa12fa1076b8c011d4306e421b3301ade0247579160dc9e225dcdf5a0",
    "controlled_language.csv": "e802bd047407f8c7ef48bf975781942faaf8c69288665f201c461925e553804e",
}

TARGET_DIR = Path(__file__).resolve().parent.parent / "data" / "idc"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch(name: str, expected: str, target_dir: Path) -> None:
    target = target_dir / name
    if target.exists() and sha256(target.read_bytes()) == expected:
        print(f"ok (present)    {name}")
        return

    url = f"{BASE_URL}/data/{name}"
    with urllib.request.urlopen(url, timeout=120) as response:  # noqa: S310 - fixed HTTPS URL
        payload = response.read()

    actual = sha256(payload)
    if actual != expected:
        raise SystemExit(
            f"ERROR: checksum of {name} differs.\n  expected: {expected}\n  received: {actual}"
        )

    target.write_bytes(payload)
    print(f"ok (loaded)     {name}  {len(payload) / 1_000_000:.1f} MB")


def main() -> int:
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    for name, expected in FILES.items():
        fetch(name, expected, TARGET_DIR)
    print(f"\nDataset is in {TARGET_DIR}")
    print("License CC BY 4.0, citation requirement see DATA.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
