---
name: flight-search
description: Search Google Flights through the fast_flights wrapper with user-friendly formatting and practical filters like time window, max price, and aircraft family.
---

# Flight Search

Use this skill when you need to look up flights with readable output instead of raw Google Flights payloads.

This skill now ships with a concrete packaged helper module/API wrapper:
- `base/api.py`
- `base/__init__.py`
- CLI wrapper at `scripts/flight_search_base.py`
- runnable example at `examples/example_runner.py`
- setup notes in `references/setup.md`

The skill assumes the host environment exposes or installs:
- `find_flights(...)`
- `format_itineraries(...)`
- `SearchRequest`
- `search_flights(...)`
- `search_date_window(...)`

## What this skill is for

Use it for queries like:
- "Find BLR to BOM flights tomorrow after 4pm"
- "Only show Airbus flights"
- "Only show flights below 8k"
- "Show me the best evening options with clean formatting"

The formatter is designed to show:
- city + airport code
- airline
- flight number
- aircraft type
- stop summary
- overnight arrivals
- segment-level details
- terminals when the source provides them

## Quick start

If you want a concrete file to run or adapt, start from:
- `scripts/flight_search_base.py`

```python
from fast_flights import find_flights, format_itineraries

response = find_flights(
    "BLR",
    "BOM",
    date="2026-04-25",
    after="16:00",
    currency="INR",
    max_results=5,
)

print(format_itineraries(response.results))
```

## Main helper

Prefer `find_flights(...)` for most user-facing use cases.

### Supported arguments

```python
find_flights(
    origin: str,
    destination: str,
    *,
    date: str,
    after: str | datetime.time | None = None,
    before: str | datetime.time | None = None,
    max_price: int | None = None,
    aircraft: str | None = None,
    max_results: int | None = None,
    seat: str = "economy",
    trip: str = "one-way",
    adults: int = 1,
    language: str = "",
    currency: str = "",
    sources: tuple[str, ...] = ("google-flights",),
    sort: str = "cheapest",
)
```

### Meaning of the key filters

- `after="16:00"` → departures at or after 4pm
- `before="21:00"` → departures at or before 9pm
- `max_price=8000` → price ceiling
- `aircraft="airbus"` → substring match on aircraft type, case-insensitive
- `aircraft="boeing"` works the same way

## Common recipes

### 1. Evening flights

```python
response = find_flights(
    "BLR",
    "BOM",
    date="2026-04-25",
    after="16:00",
    currency="INR",
    max_results=5,
)
print(format_itineraries(response.results))
```

### 2. Only Airbus flights

```python
response = find_flights(
    "BLR",
    "BOM",
    date="2026-04-25",
    aircraft="airbus",
    currency="INR",
)
print(format_itineraries(response.results))
```

### 3. Only flights below 8k

```python
response = find_flights(
    "BLR",
    "BOM",
    date="2026-04-25",
    max_price=8000,
    currency="INR",
)
print(format_itineraries(response.results))
```

### 4. Airbus flights below 8k after 4pm

```python
response = find_flights(
    "BLR",
    "BOM",
    date="2026-04-25",
    after="16:00",
    max_price=8000,
    aircraft="airbus",
    currency="INR",
    max_results=5,
)
print(format_itineraries(response.results))
```

### 5. Narrow time window

```python
response = find_flights(
    "BLR",
    "BOM",
    date="2026-04-25",
    after="18:00",
    before="22:00",
    currency="INR",
)
print(format_itineraries(response.results))
```

## Example output shape

```text
1. Bengaluru (BLR) → Mumbai (BOM)
   Price: 6009 INR
   Source: Google Flights
   Stops: non-stop
   Airlines: Air India
   Departure: 2026-04-25 22:30
   Arrival: 2026-04-26 00:35 (overnight)
   Duration: 125m
   Segment 1: Bengaluru (BLR) → Mumbai (BOM)
      Kempegowda International Airport Bengaluru
      Chhatrapati Shivaji Maharaj International Airport Mumbai
      Flight: AI 2840
      Aircraft: Airbus A320neo
      Time: 2026-04-25 22:30 → 2026-04-26 00:35
      Segment duration: 125m
```

## Lower-level usage

Use `SearchRequest(...)` + `search_flights(...)` if you need more direct control.

```python
from datetime import time
from fast_flights import FlightQuery, Passengers, SearchRequest, TimeWindow, create_query, search_flights

query = create_query(
    flights=[FlightQuery(date="2026-04-25", from_airport="BLR", to_airport="BOM")],
    seat="economy",
    trip="one-way",
    passengers=Passengers(adults=1),
    currency="INR",
)

request = SearchRequest(
    query=query,
    departure_window=TimeWindow(start=time(16, 0), end=time(23, 59)),
    max_price=8000,
    aircraft_query="airbus",
    max_results=5,
)

response = search_flights(request)
```

## Date-window search

Use `search_date_window(...)` when comparing a span of dates.

```python
from datetime import date
from fast_flights import FlightQuery, SearchRequest, create_query, search_date_window

request = SearchRequest(
    query=create_query(
        flights=[FlightQuery(date="2026-04-25", from_airport="BLR", to_airport="BOM")],
        currency="INR",
    ),
    max_price=8000,
    aircraft_query="airbus",
    max_results=10,
)

window = search_date_window(
    request,
    start_date=date(2026, 4, 25),
    end_date=date(2026, 4, 27),
)
```

## Practical rules

1. Prefer `find_flights(...)` unless you truly need the lower-level API.
2. Always set `currency="INR"` or your preferred currency when comparing prices.
3. Use `after`/`before` for user-facing time filtering.
4. Use `aircraft="airbus"` or `aircraft="boeing"` instead of exact plane strings unless the user asked for a specific model.
5. Run `format_itineraries(response.results)` for final output instead of dumping raw objects.

## Caveats

- Terminal data is shown only when Google’s payload includes it.
- Aircraft filtering is a case-insensitive substring match against parsed plane type strings.
- Overnight arrivals are inferred from normalized segment dates/times.
- Placeholder sources like ixigo/cleartrip are not the main path unless adapters are implemented.

## Good defaults

For most chat-style tasks, use:

```python
response = find_flights(
    ORIGIN,
    DESTINATION,
    date=DATE,
    after="16:00",
    max_price=8000,
    aircraft="airbus",
    currency="INR",
    max_results=5,
)
print(format_itineraries(response.results))
```

## When not to use this skill

Skip this skill if the task is about:
- scraping new providers
- changing parser internals
- debugging malformed upstream payloads
- training / benchmarking models

That is code work, not flight lookup workflow.
