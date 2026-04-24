# Setup

This skill pack includes three concrete integration layers plus a local dependency bootstrap:

- packaged helper module at `base/api.py`
- package exports at `base/__init__.py`
- CLI wrapper at `scripts/flight_search_base.py`
- repo-local installer at `scripts/install_local_deps.py`
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

If ordinary `pip install -r requirements.txt` works in your environment, use that.
You can use either the repo root file or the skill-local file:

```bash
python -m pip install -r requirements.txt
# or
python -m pip install -r skills/flight-search/requirements.txt
```

If the host blocks system-wide installs or lacks `python3-venv`, use the repo-local installer instead:

```bash
python skills/flight-search/scripts/install_local_deps.py
```

That installer prefers `skills/flight-search/requirements.txt`, falls back to the repo root `requirements.txt`, and installs dependencies under `skills/flight-search/vendor/`.
The helper module/CLI automatically imports from there.

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

So the host project must make `fast_flights` importable, either through a normal install or through the repo-local `vendor/` path populated by `scripts/install_local_deps.py`.

## Typical integration pattern

1. Copy this skill folder into your Claude/Codex skills directory.
2. Make `fast-flights` importable, either with `python -m pip install -r requirements.txt` or with `python skills/flight-search/scripts/install_local_deps.py`.
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
