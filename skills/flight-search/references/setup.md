# Setup

This skill pack includes a base helper script at:

- `scripts/flight_search_base.py`

## What the helper gives you

It defines:

- `FlightSearchParams`
- `search_flights_with_filters(...)`
- `search_and_format(...)`
- `params_from_dict(...)`
- a small CLI entrypoint

## Dependency expectation

The helper imports the `fast_flights` Python API:

```python
from fast_flights import (
    FlightQuery,
    Passengers,
    SearchRequest,
    TimeWindow,
    create_query,
    format_itineraries,
    search_flights,
)
```

So the host project must already have the patched `fast_flights` implementation available.

## Typical integration pattern

1. Copy this skill folder into your Claude/Codex skills directory.
2. Copy `scripts/flight_search_base.py` into your project if you want a concrete wrapper/API file.
3. Make sure the environment has the required `fast_flights` package or source tree.
4. Call:

```python
from flight_search_base import FlightSearchParams, search_and_format

params = FlightSearchParams(
    origin="BLR",
    destination="BOM",
    date="2026-04-25",
    after="16:00",
    max_price=8000,
    aircraft="airbus",
    currency="INR",
)

print(search_and_format(params))
```

## CLI usage

```bash
python scripts/flight_search_base.py BLR BOM 2026-04-25 \
  --after 16:00 \
  --max-price 8000 \
  --aircraft airbus \
  --currency INR
```

## Why this exists

The `SKILL.md` alone documents the workflow, but many Claude/Codex users also want a concrete base script/API file they can run or adapt. This file is the bridge.
