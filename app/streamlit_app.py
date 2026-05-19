from __future__ import annotations

import runpy
from pathlib import Path


ISKRA_FORGE_PAGE = Path(__file__).resolve().parent / "pages" / "00_Iskra_Forge.py"


if __name__ == "__main__":
    runpy.run_path(str(ISKRA_FORGE_PAGE), run_name="__main__")
