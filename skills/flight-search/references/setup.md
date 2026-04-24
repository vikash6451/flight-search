# Setup

This skill pack includes three concrete integration layers:

- packaged helper module at `base/api.py`
- package exports at `base/__init__.py`
- CLI wrapper at `scripts/flight_search_base.py`
- example runner at `examples/example_runner.py`

## What the helper gives you

The packaged module exposes:

- `FlightSearchParams`
- `search_flights_with_filters(...)`
- `search_and_format(...)`
- `params_from_dict(...)`
- `build_departure_window(...)`
- `parse_time(...)`

The CLI wrapper gives you a small executable entrypoint.

## Install dependencies

At minimum install the Python dependency from the repo root:

```bash
python -m pip install -r requirements.txt
```

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
2. Install `requirements.txt` or ensure `fast-flights` is already available.
3. Import from the packaged module:

```python
from base import FlightSearchParams, search_and_format

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
