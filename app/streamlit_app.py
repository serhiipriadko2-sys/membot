from __future__ import annotations

import runpy
from pathlib import Path


SIGNAL_FORGE_PAGE = Path(__file__).resolve().parent / "pages" / "00_Signal_Forge.py"


if __name__ == "__main__":
    runpy.run_path(str(SIGNAL_FORGE_PAGE), run_name="__main__")
