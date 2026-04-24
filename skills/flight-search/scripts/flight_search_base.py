from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import time
from typing import Any

from fast_flights import (
    FlightQuery,
    Passengers,
    SearchRequest,
    TimeWindow,
    create_query,
    format_itineraries,
    search_flights,
)


@dataclass
class FlightSearchParams:
    origin: str
    destination: str
    date: str
    after: str | time | None = None
    before: str | time | None = None
    max_price: int | None = None
    aircraft: str | None = None
    max_results: int | None = 5
    seat: str = "economy"
    trip: str = "one-way"
    adults: int = 1
    language: str = ""
    currency: str = ""
    sort: str = "cheapest"
    sources: tuple[str, ...] = ("google-flights",)


def search_flights_with_filters(params: FlightSearchParams):
    query = create_query(
        flights=[
            FlightQuery(
                date=params.date,
                from_airport=params.origin,
                to_airport=params.destination,
            )
        ],
        seat=params.seat,
        trip=params.trip,
        passengers=Passengers(adults=params.adults),
        language=params.language,
        currency=params.currency,
    )
    request = SearchRequest(
        query=query,
        sources=tuple(params.sources),
        sort=params.sort,
        departure_window=build_departure_window(params.after, params.before),
        max_results=params.max_results,
        max_price=params.max_price,
        aircraft_query=params.aircraft,
    )
    return search_flights(request)


def search_and_format(params: FlightSearchParams) -> str:
    response = search_flights_with_filters(params)
    return format_itineraries(response.results)


def build_departure_window(after: str | time | None, before: str | time | None) -> TimeWindow | None:
    if after is None and before is None:
        return None
    start = parse_time(after) if after is not None else time(0, 0)
    end = parse_time(before) if before is not None else time(23, 59)
    return TimeWindow(start=start, end=end)


def parse_time(value: str | time) -> time:
    if isinstance(value, time):
        return value
    hour_str, minute_str = value.strip().split(":", 1)
    return time(int(hour_str), int(minute_str))


def params_from_dict(data: dict[str, Any]) -> FlightSearchParams:
    return FlightSearchParams(
        origin=data["origin"],
        destination=data["destination"],
        date=data["date"],
        after=data.get("after"),
        before=data.get("before"),
        max_price=data.get("max_price"),
        aircraft=data.get("aircraft"),
        max_results=data.get("max_results", 5),
        seat=data.get("seat", "economy"),
        trip=data.get("trip", "one-way"),
        adults=data.get("adults", 1),
        language=data.get("language", ""),
        currency=data.get("currency", ""),
        sort=data.get("sort", "cheapest"),
        sources=tuple(data.get("sources", ("google-flights",))),
    )


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
