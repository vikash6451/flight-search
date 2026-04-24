from __future__ import annotations

import argparse
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

from base import FlightSearchParams, search_and_format


def main() -> None:
    parser = argparse.ArgumentParser(description="Search flights with simple filters.")
    parser.add_argument("origin")
    parser.add_argument("destination")
    parser.add_argument("date")
    parser.add_argument("--after")
    parser.add_argument("--before")
    parser.add_argument("--max-price", type=int)
    parser.add_argument("--aircraft")
    parser.add_argument("--max-results", type=int, default=5)
    parser.add_argument("--seat", default="economy")
    parser.add_argument("--trip", default="one-way")
    parser.add_argument("--adults", type=int, default=1)
    parser.add_argument("--language", default="")
    parser.add_argument("--currency", default="")
    parser.add_argument("--sort", default="cheapest")
    args = parser.parse_args()

    params = FlightSearchParams(
        origin=args.origin,
        destination=args.destination,
        date=args.date,
        after=args.after,
        before=args.before,
        max_price=args.max_price,
        aircraft=args.aircraft,
        max_results=args.max_results,
        seat=args.seat,
        trip=args.trip,
        adults=args.adults,
        language=args.language,
        currency=args.currency,
        sort=args.sort,
    )
    print(search_and_format(params))


if __name__ == "__main__":
    main()
