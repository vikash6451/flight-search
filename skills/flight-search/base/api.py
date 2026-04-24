from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from pathlib import Path
from typing import Any


_VENDOR_PATH = Path(__file__).resolve().parent.parent / "vendor"


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


def _load_fast_flights_api() -> dict[str, Any]:
    import sys

    if _VENDOR_PATH.exists() and str(_VENDOR_PATH) not in sys.path:
        sys.path.insert(0, str(_VENDOR_PATH))

    try:
        from fast_flights import (
            FlightQuery,
            Passengers,
            SearchRequest,
            TimeWindow,
            create_query,
            format_itineraries,
            search_flights,
        )
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "fast_flights is not installed. Run `python skills/flight-search/scripts/install_local_deps.py` "
            "to install dependencies into the repo-local vendor directory, or otherwise make fast-flights "
            "importable in this environment."
        ) from exc

    return {
        "FlightQuery": FlightQuery,
        "Passengers": Passengers,
        "SearchRequest": SearchRequest,
        "TimeWindow": TimeWindow,
        "create_query": create_query,
        "format_itineraries": format_itineraries,
        "search_flights": search_flights,
    }


def search_flights_with_filters(params: FlightSearchParams):
    api = _load_fast_flights_api()
    query = api["create_query"](
        flights=[
            api["FlightQuery"](
                date=params.date,
                from_airport=params.origin,
                to_airport=params.destination,
            )
        ],
        seat=params.seat,
        trip=params.trip,
        passengers=api["Passengers"](adults=params.adults),
        language=params.language,
        currency=params.currency,
    )
    request = api["SearchRequest"](
        query=query,
        sources=tuple(params.sources),
        sort=params.sort,
        departure_window=build_departure_window(params.after, params.before),
        max_results=params.max_results,
        max_price=params.max_price,
        aircraft_query=params.aircraft,
    )
    return api["search_flights"](request)


def search_and_format(params: FlightSearchParams) -> str:
    api = _load_fast_flights_api()
    response = search_flights_with_filters(params)
    return api["format_itineraries"](response.results)


def build_departure_window(after: str | time | None, before: str | time | None):
    if after is None and before is None:
        return None
    api = _load_fast_flights_api()
    start = parse_time(after) if after is not None else time(0, 0)
    end = parse_time(before) if before is not None else time(23, 59)
    return api["TimeWindow"](start=start, end=end)


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
