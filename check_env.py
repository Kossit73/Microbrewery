"""
Lightweight dependency check for the microbrewery model.
Run this script after creating a virtual environment to confirm that
numpy, pandas, streamlit, and openpyxl are available.
"""
from __future__ import annotations

import importlib
import sys
from typing import List

REQUIRED_PACKAGES: List[str] = ["numpy", "pandas", "streamlit", "openpyxl"]


def _status_line(pkg: str) -> str:
    try:
        mod = importlib.import_module(pkg)
    except Exception as exc:  # noqa: BLE001
        return f"[MISSING] {pkg} — install with 'pip install {pkg}' (error: {exc})"
    version = getattr(mod, "__version__", "?")
    return f"[OK] {pkg} {version}"


def main() -> int:
    print("Dependency check\n==================")
    statuses = [_status_line(pkg) for pkg in REQUIRED_PACKAGES]
    for line in statuses:
        print(line)

    missing = [s for s in statuses if s.startswith("[MISSING]")]
    if missing:
        print(
            "\nOne or more packages are missing. "
            "Install online with 'pip install -r requirements.txt' "
            "or offline using pre-downloaded wheels: "
            "'pip install --no-index --find-links=./vendor -r requirements.txt'."
        )
        return 1
    print("\nAll core dependencies are present.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
