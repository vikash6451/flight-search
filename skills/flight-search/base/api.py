from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
import json
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any, Sequence
from urllib.parse import urlencode


_VENDOR_PATH = Path(__file__).resolve().parent.parent / "vendor"


@dataclass(frozen=True)
class TimeWindow:
    start: time
    end: time

    def contains(self, value: time) -> bool:
        if self.start <= self.end:
            return self.start <= value <= self.end
        return value >= self.start or value <= self.end


@dataclass(frozen=True)
class NormalizedSegment:
    origin_code: str
    origin_name: str
    destination_code: str
    destination_name: str
    departure_at: datetime
    arrival_at: datetime
    duration_minutes: int
    plane_type: str
    flight_number: str | None = None
    departure_terminal: str | None = None
    arrival_terminal: str | None = None


@dataclass(frozen=True)
class NormalizedItinerary:
    source: str
    source_label: str
    price: int
    currency: str | None
    airlines: tuple[str, ...]
    departure_at: datetime
    arrival_at: datetime
    duration_minutes: int
    stop_count: int
    booking_url: str
    segments: tuple[NormalizedSegment, ...]
    raw: Any


@dataclass(frozen=True)
class SearchResponse:
    results: tuple[NormalizedItinerary, ...]
    raw: Any
    mode: str
    errors: dict[str, str] = field(default_factory=dict)


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
    sources: tuple[str, ...] = ("google-flights", "letsfg")


def _load_fast_flights_api() -> dict[str, Any]:
    import sys

    if _VENDOR_PATH.exists() and str(_VENDOR_PATH) not in sys.path:
        sys.path.insert(0, str(_VENDOR_PATH))

    try:
        import fast_flights
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "fast_flights is not installed. Run `python skills/flight-search/scripts/install_local_deps.py` "
            "to install dependencies into the repo-local vendor directory, or otherwise make fast-flights "
            "importable in this environment."
        ) from exc

    exports = {name: getattr(fast_flights, name) for name in dir(fast_flights) if not name.startswith("_")}
    exports["module"] = fast_flights
    exports["compat_mode"] = "search_v2" if "SearchRequest" in exports and "search_flights" in exports else "legacy_rc0"
    return exports


def search_flights_with_filters(params: FlightSearchParams) -> SearchResponse:
    results: list[NormalizedItinerary] = []
    raw: dict[str, Any] = {}
    errors: dict[str, str] = {}
    modes: list[str] = []

    if "google-flights" in params.sources:
        try:
            google_response = _search_google_provider(params)
            results.extend(google_response.results)
            raw["google-flights"] = google_response.raw
            errors.update(google_response.errors)
            modes.append(google_response.mode)
        except Exception as exc:
            errors["google-flights"] = f"{type(exc).__name__}: {exc}"

    wants_letsfg = "letsfg" in params.sources
    underfilled = params.max_results is None or len(results) < params.max_results
    if wants_letsfg and underfilled:
        try:
            letsfg_limit = max(params.max_results or 10, 10)
            letsfg_payload = _run_letsfg_search(params, limit=letsfg_limit)
            raw["letsfg"] = letsfg_payload
            results.extend(_normalize_letsfg_results(letsfg_payload, params=params))
            modes.append("letsfg")
        except Exception as exc:
            errors["letsfg"] = f"{type(exc).__name__}: {exc}"

    filtered = _filter_itineraries(
        _dedupe_itineraries(results),
        departure_window=build_departure_window(params.after, params.before),
        max_price=params.max_price,
        aircraft_query=params.aircraft,
    )
    ranked = _rank_itineraries(filtered, mode=params.sort)
    if params.max_results is not None:
        ranked = ranked[: params.max_results]
    mode = "+".join(modes) if modes else "none"
    return SearchResponse(results=tuple(ranked), raw=raw, mode=mode, errors=errors)


def _search_google_provider(params: FlightSearchParams) -> SearchResponse:
    api = _load_fast_flights_api()
    if api["compat_mode"] == "search_v2":
        return _search_with_v2_api(api, params)
    return _search_with_legacy_api(api, params)


def search_and_format(params: FlightSearchParams) -> str:
    response = search_flights_with_filters(params)
    rendered = format_itineraries(response.results)
    if response.errors and not response.results:
        details = "; ".join(f"{source}: {error}" for source, error in response.errors.items())
        return f"{rendered}\n\nProvider errors: {details}"
    return rendered


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
        sources=tuple(data.get("sources", ("google-flights", "letsfg"))),
    )


def format_itineraries(itineraries: Sequence[NormalizedItinerary]) -> str:
    if not itineraries:
        return "No matching itineraries."

    blocks: list[str] = []
    for index, itinerary in enumerate(itineraries, start=1):
        first_segment = itinerary.segments[0]
        last_segment = itinerary.segments[-1]
        price = str(itinerary.price) if itinerary.currency is None else f"{itinerary.price} {itinerary.currency}"
        lines = [
            f"{index}. {_airport_label(first_segment.origin_name, first_segment.origin_code)} → {_airport_label(last_segment.destination_name, last_segment.destination_code)}",
            f"   Price: {price}",
            f"   Source: {itinerary.source_label}",
            f"   Stops: {_stop_summary(itinerary)}",
            f"   Airlines: {', '.join(itinerary.airlines)}",
            f"   Departure: {_format_trip_datetime(itinerary.departure_at, base_date=itinerary.departure_at.date())}",
            f"   Arrival: {_format_trip_datetime(itinerary.arrival_at, base_date=itinerary.departure_at.date(), overnight_label=True)}",
            f"   Duration: {itinerary.duration_minutes}m",
        ]
        for seg_index, segment in enumerate(itinerary.segments, start=1):
            lines.extend(
                [
                    f"   Segment {seg_index}: {_airport_label(segment.origin_name, segment.origin_code)} → {_airport_label(segment.destination_name, segment.destination_code)}",
                    f"      {segment.origin_name}",
                    f"      {segment.destination_name}",
                    f"      Flight: {segment.flight_number or 'unknown'}",
                    f"      Aircraft: {segment.plane_type or 'unknown'}",
                    *(
                        [f"      Terminal: {segment.departure_terminal or '?'} → {segment.arrival_terminal or '?'}"]
                        if segment.departure_terminal or segment.arrival_terminal
                        else []
                    ),
                    f"      Time: {_format_segment_datetime(segment.departure_at)} → {_format_segment_datetime(segment.arrival_at, base_date=segment.departure_at.date())}",
                    f"      Segment duration: {segment.duration_minutes}m",
                ]
            )
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def _search_with_v2_api(api: dict[str, Any], params: FlightSearchParams) -> SearchResponse:
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
        departure_window=_coerce_v2_time_window(api, build_departure_window(params.after, params.before)),
        max_results=params.max_results,
        max_price=params.max_price,
        aircraft_query=params.aircraft,
    )
    raw_response = api["search_flights"](request)
    return SearchResponse(results=tuple(raw_response.results), raw=raw_response, mode="search_v2")


def _search_with_legacy_api(api: dict[str, Any], params: FlightSearchParams) -> SearchResponse:
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
        max_stops=None,
    )
    raw_results = _get_legacy_flights(api, query)
    normalized = [_normalize_legacy_itinerary(item, query=query) for item in raw_results]
    filtered = _filter_itineraries(
        normalized,
        departure_window=build_departure_window(params.after, params.before),
        max_price=params.max_price,
        aircraft_query=params.aircraft,
    )
    ranked = _rank_itineraries(filtered, mode=params.sort)
    if params.max_results is not None:
        ranked = ranked[: params.max_results]
    return SearchResponse(results=tuple(ranked), raw=raw_results, mode="legacy_rc0")


def _coerce_v2_time_window(api: dict[str, Any], window: TimeWindow | None):
    if window is None:
        return None
    return api["TimeWindow"](start=window.start, end=window.end)


def _get_legacy_flights(api: dict[str, Any], query: Any):
    try:
        return api["get_flights"](query)
    except AttributeError as exc:
        message = str(exc)
        if "'NoneType' object has no attribute 'text'" not in message:
            raise
        return _parse_legacy_results_from_html(api, query)
    except IndexError:
        return _parse_legacy_results_from_html(api, query, defensive=True)


def _parse_legacy_results_from_html(api: dict[str, Any], query: Any, *, defensive: bool = False):
    from selectolax.lexbor import LexborHTMLParser

    fetch_html = getattr(api["module"].fetcher, "fetch_flights_html")
    parse_js = getattr(api["module"].parser, "parse_js")

    html = fetch_html(query)
    parser = LexborHTMLParser(html)

    script = parser.css_first("script.ds\\:1")
    if script is None:
        for candidate in parser.css("script"):
            text = candidate.text() or ""
            if "AF_initDataCallback" in text and "key: 'ds:1'" in text:
                script = candidate
                break

    if script is None:
        title = parser.css_first("title")
        title_text = title.text(strip=True) if title is not None else "(no title)"
        html_prefix = html[:500].replace("\n", " ").strip()
        raise RuntimeError(
            "Google Flights response did not contain the expected ds:1 data script. "
            f"Page title: {title_text}. HTML prefix: {html_prefix}"
        )

    if defensive:
        return _parse_legacy_js_defensively(api, script.text())
    try:
        return parse_js(script.text())
    except IndexError:
        return _parse_legacy_js_defensively(api, script.text())


def _legacy_price_from_row(price_field: Any) -> int | None:
    try:
        price = price_field[0][1]
    except (IndexError, TypeError):
        return None
    return int(price) if price is not None else None


def _parse_legacy_js_defensively(api: dict[str, Any], js: str):
    import rjsonc

    model = api["module"].model
    parser_module = api["module"].parser
    meta_list_cls = getattr(parser_module, "MetaList")

    payload = js.split("data:", 1)[1].rsplit(",", 1)[0]
    data = rjsonc.loads(payload)

    alliances = [model.Alliance(code=code, name=name) for code, name in data[7][1][0]]
    airlines_meta = [model.Airline(code=code, name=name) for code, name in data[7][1][1]]

    flights = meta_list_cls()
    for row in data[3][0]:
        price = _legacy_price_from_row(row[1] if len(row) > 1 else None)
        if price is None:
            continue
        try:
            flight = row[0]
            segments = []
            for single_flight in flight[2]:
                from_airport = model.Airport(code=single_flight[3], name=single_flight[4])
                to_airport = model.Airport(code=single_flight[6], name=single_flight[5])
                departure = model.SimpleDatetime(date=single_flight[20], time=single_flight[8])
                arrival = model.SimpleDatetime(date=single_flight[21], time=single_flight[10])
                segments.append(
                    model.SingleFlight(
                        from_airport=from_airport,
                        to_airport=to_airport,
                        departure=departure,
                        arrival=arrival,
                        duration=single_flight[11],
                        plane_type=single_flight[17],
                    )
                )
            extras = flight[22] if len(flight) > 22 else []
            carbon_emission = extras[7] if len(extras) > 7 else 0
            typical_carbon_emission = extras[8] if len(extras) > 8 else 0
            flights.append(
                model.Flights(
                    type=flight[0],
                    price=price,
                    airlines=flight[1],
                    flights=segments,
                    carbon=model.CarbonEmission(
                        typical_on_route=typical_carbon_emission,
                        emission=carbon_emission,
                    ),
                )
            )
        except (IndexError, TypeError):
            continue
    flights.metadata = model.JsMetadata(alliances=alliances, airlines=airlines_meta)
    return flights


def _normalize_legacy_itinerary(flight: Any, *, query: Any) -> NormalizedItinerary:
    segments = tuple(_normalize_legacy_segment(item) for item in flight.flights)
    departure_at = segments[0].departure_at
    arrival_at = segments[-1].arrival_at
    duration_minutes = int((arrival_at - departure_at).total_seconds() // 60)
    currency = getattr(query, "currency", None) or None
    return NormalizedItinerary(
        source="google-flights",
        source_label="Google Flights",
        price=int(flight.price),
        currency=currency,
        airlines=tuple(flight.airlines),
        departure_at=departure_at,
        arrival_at=arrival_at,
        duration_minutes=duration_minutes,
        stop_count=max(len(segments) - 1, 0),
        booking_url=_booking_url_for_query(query),
        segments=segments,
        raw=flight,
    )


def _normalize_legacy_segment(segment: Any) -> NormalizedSegment:
    departure_at = _datetime_from_parts(segment.departure.date, segment.departure.time)
    arrival_at = _datetime_from_parts(
        segment.arrival.date,
        segment.arrival.time,
        fallback=departure_at + timedelta(minutes=segment.duration),
    )
    return NormalizedSegment(
        origin_code=segment.from_airport.code,
        origin_name=segment.from_airport.name,
        destination_code=segment.to_airport.code,
        destination_name=segment.to_airport.name,
        departure_at=departure_at,
        arrival_at=arrival_at,
        duration_minutes=int(segment.duration),
        plane_type=getattr(segment, "plane_type", "") or "",
        flight_number=getattr(segment, "flight_number", None),
        departure_terminal=_short_terminal(getattr(segment, "departure_terminal", None)),
        arrival_terminal=_short_terminal(getattr(segment, "arrival_terminal", None)),
    )


def _normalize_letsfg_results(payload: dict[str, Any], *, params: FlightSearchParams) -> tuple[NormalizedItinerary, ...]:
    offers = payload.get("offers") or []
    normalized = []
    for offer in offers:
        try:
            normalized.append(_normalize_letsfg_offer(offer, params=params))
        except (KeyError, TypeError, ValueError):
            continue
    return tuple(normalized)


def _normalize_letsfg_offer(offer: dict[str, Any], *, params: FlightSearchParams) -> NormalizedItinerary:
    outbound = offer["outbound"]
    raw_segments = outbound["segments"]
    segments = tuple(_normalize_letsfg_segment(segment) for segment in raw_segments)
    departure_at = segments[0].departure_at
    arrival_at = segments[-1].arrival_at
    duration_minutes = int((arrival_at - departure_at).total_seconds() // 60)
    if duration_minutes < 0:
        duration_minutes = int((outbound.get("total_duration_seconds") or 0) // 60)
    price = offer.get("price_normalized") or offer.get("price")
    currency = params.currency or offer.get("currency") or None
    source = offer.get("source") or "unknown"
    return NormalizedItinerary(
        source=f"letsfg:{source}",
        source_label=f"LetsFG ({source})",
        price=int(round(float(price))),
        currency=currency,
        airlines=tuple(offer.get("airlines") or [segment.flight_number or "unknown" for segment in segments]),
        departure_at=departure_at,
        arrival_at=arrival_at,
        duration_minutes=duration_minutes,
        stop_count=int(outbound.get("stopovers") if outbound.get("stopovers") is not None else max(len(segments) - 1, 0)),
        booking_url=offer.get("booking_url") or "",
        segments=segments,
        raw=offer,
    )


def _normalize_letsfg_segment(segment: dict[str, Any]) -> NormalizedSegment:
    departure_at = _parse_letsfg_datetime(segment["departure"])
    arrival_at = _parse_letsfg_datetime(segment["arrival"])
    duration_minutes = int((segment.get("duration_seconds") or 0) // 60)
    if duration_minutes <= 0:
        duration_minutes = int((arrival_at - departure_at).total_seconds() // 60)
    return NormalizedSegment(
        origin_code=segment.get("origin") or "",
        origin_name=segment.get("origin_city") or f"{segment.get('origin') or ''} Airport",
        destination_code=segment.get("destination") or "",
        destination_name=segment.get("destination_city") or f"{segment.get('destination') or ''} Airport",
        departure_at=departure_at,
        arrival_at=arrival_at,
        duration_minutes=duration_minutes,
        plane_type=segment.get("aircraft") or "",
        flight_number=segment.get("flight_no") or segment.get("airline"),
    )


def _parse_letsfg_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is not None:
        return parsed.replace(tzinfo=None)
    return parsed


def _run_letsfg_search(params: FlightSearchParams, *, limit: int) -> dict[str, Any]:
    command = os.environ.get("LETSFG_COMMAND") or shutil.which("letsfg")
    if command is None:
        raise RuntimeError("LetsFG CLI not found. Install with `pip install letsfg` or set LETSFG_COMMAND.")

    args = [
        command,
        "search",
        params.origin,
        params.destination,
        params.date,
        "--mode",
        "fast",
        "--max-browsers",
        os.environ.get("LETSFG_MAX_BROWSERS", "4"),
        "--limit",
        str(limit),
        "--json",
    ]
    if params.currency:
        args.extend(["--currency", params.currency])

    xvfb = shutil.which("xvfb-run")
    if xvfb is not None and os.environ.get("DISPLAY") is None:
        args = [xvfb, "-a", *args]

    completed = subprocess.run(args, check=False, text=True, capture_output=True, timeout=240)
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        raise RuntimeError(f"LetsFG search failed with exit {completed.returncode}: {detail[:500]}")
    text = completed.stdout
    start = text.find("{")
    if start < 0:
        raise RuntimeError(f"LetsFG did not return JSON: {text[:500]}")
    return json.loads(text[start:])


def _dedupe_itineraries(itineraries: Sequence[NormalizedItinerary]) -> list[NormalizedItinerary]:
    best_by_key: dict[tuple[Any, ...], NormalizedItinerary] = {}
    for item in itineraries:
        key = _itinerary_dedupe_key(item)
        existing = best_by_key.get(key)
        if existing is None or item.price < existing.price:
            best_by_key[key] = item
    return list(best_by_key.values())


def _itinerary_dedupe_key(item: NormalizedItinerary) -> tuple[Any, ...]:
    return (
        tuple((segment.origin_code, segment.destination_code, segment.flight_number) for segment in item.segments),
        item.departure_at,
        item.arrival_at,
    )


def _filter_itineraries(
    itineraries: Sequence[NormalizedItinerary],
    *,
    departure_window: TimeWindow | None,
    max_price: int | None,
    aircraft_query: str | None,
) -> list[NormalizedItinerary]:
    results = list(itineraries)
    if departure_window is not None:
        results = [item for item in results if departure_window.contains(item.departure_at.time())]
    if max_price is not None:
        results = [item for item in results if item.price <= max_price]
    if aircraft_query is not None and aircraft_query.strip():
        needle = aircraft_query.strip().lower()
        results = [
            item
            for item in results
            if any(needle in (segment.plane_type or "").lower() for segment in item.segments)
        ]
    return results


def _rank_itineraries(itineraries: Sequence[NormalizedItinerary], *, mode: str) -> list[NormalizedItinerary]:
    if mode == "cheapest":
        key = lambda item: (item.price, item.duration_minutes, item.departure_at)
    elif mode == "fastest":
        key = lambda item: (item.duration_minutes, item.price, item.departure_at)
    elif mode == "balanced":
        key = lambda item: (
            item.price + item.duration_minutes + (item.stop_count * 90),
            item.price,
            item.duration_minutes,
            item.departure_at,
        )
    else:
        raise ValueError(f"unknown sort mode: {mode}")
    return sorted(itineraries, key=key)


def _booking_url_for_query(query: Any) -> str:
    if hasattr(query, "url"):
        return query.url()
    return "https://www.google.com/travel/flights?" + urlencode({"q": str(query)})


def _datetime_from_parts(
    date_parts: tuple[int, int, int],
    time_parts: Sequence[int | None],
    *,
    fallback: datetime | None = None,
) -> datetime:
    if len(time_parts) >= 2:
        hour, minute = time_parts[0], time_parts[1]
    elif len(time_parts) == 1:
        hour, minute = time_parts[0], 0
    else:
        hour, minute = None, None
    if hour is None or minute is None:
        if fallback is None:
            raise ValueError(f"incomplete time parts without fallback: {time_parts!r}")
        return fallback
    return datetime(
        year=date_parts[0],
        month=date_parts[1],
        day=date_parts[2],
        hour=hour,
        minute=minute,
    )


def _stop_label(stop_count: int) -> str:
    if stop_count <= 0:
        return "non-stop"
    if stop_count == 1:
        return "1 stop"
    return f"{stop_count} stops"


def _stop_summary(itinerary: NormalizedItinerary) -> str:
    base = _stop_label(itinerary.stop_count)
    if itinerary.stop_count <= 0:
        return base
    stopovers = [
        _airport_label(segment.destination_name, segment.destination_code)
        for segment in itinerary.segments[:-1]
    ]
    return base if not stopovers else f"{base} via {', '.join(stopovers)}"


def _airport_label(name: str, code: str) -> str:
    city = _airport_city(name)
    return f"{city} ({code})" if city else code


def _airport_city(name: str) -> str | None:
    stripped = name.strip()
    if not stripped:
        return None
    marker = "Airport "
    if marker in stripped:
        suffix = stripped.split(marker)[-1].strip()
        if suffix:
            return suffix
    words = stripped.split()
    return words[-1] if words else None


def _format_trip_datetime(value: datetime, *, base_date: date, overnight_label: bool = False) -> str:
    rendered = value.strftime("%Y-%m-%d %H:%M")
    if overnight_label and value.date() > base_date:
        return f"{rendered} (overnight)"
    return rendered


def _format_segment_datetime(value: datetime, *, base_date: date | None = None) -> str:
    if base_date is not None and value.date() == base_date:
        return value.strftime("%H:%M")
    return value.strftime("%Y-%m-%d %H:%M")


def _short_terminal(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    lower = stripped.lower()
    if lower.startswith("terminal "):
        suffix = stripped.split(" ", 1)[1].strip()
        return f"T{suffix}" if suffix else None
    return stripped
