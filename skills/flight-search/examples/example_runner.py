from __future__ import annotations

import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

from base import FlightSearchParams, search_and_format


def main() -> None:
    params = FlightSearchParams(
        origin="BLR",
        destination="BOM",
        date="2026-04-25",
        after="16:00",
        max_price=8000,
        aircraft="airbus",
        currency="INR",
        max_results=5,
    )
    print(search_and_format(params))


if __name__ == "__main__":
    main()
