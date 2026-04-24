# flight-search-skill

A Claude/Codex-style skill pack for searching flights through the `fast_flights` wrapper with:

- user-friendly itinerary formatting
- price filters
- aircraft-family filters
- time-window filters
- date-window search examples
- an included packaged base module/API wrapper
- a runnable CLI script
- an example runner
- a minimal `requirements.txt`
- a repo-local dependency bootstrap for locked-down boxes
- compatibility with the published `fast-flights` package API

## Layout

```text
requirements.txt
skills/
  flight-search/
    SKILL.md
    requirements.txt
    base/
      __init__.py
      api.py
    examples/
      example_runner.py
    references/
      setup.md
    scripts/
      flight_search_base.py
      install_local_deps.py
    vendor/
      # created locally by install_local_deps.py
```

## Install

### Claude-style

Copy `skills/flight-search/` into your Claude skills directory, for example:

```bash
mkdir -p ~/.claude/skills
cp -R skills/flight-search ~/.claude/skills/
```

### Codex-style

Copy `skills/flight-search/` into your Codex skills directory, for example:

```bash
mkdir -p ~/.codex/skills
cp -R skills/flight-search ~/.codex/skills/
```

## Dependency/API compatibility

The published `fast-flights` package on PyPI currently exposes the older rc0 API surface.
That means symbols like `SearchRequest`, `search_flights`, and `format_itineraries` may be missing even though newer source checkouts include them.

This skill pack handles both shapes:

- newer source/API → uses the richer search API directly
- published rc0 package → falls back to `create_query(...)` + `get_flights(...)` and normalizes results locally
- if the rc0 parser hits the known missing-`ds:1` script bug, the helper retries with its own defensive HTML/script extraction path

On the rc0 package, airport names, aircraft type, prices, and stop counts are available, but flight numbers and terminal metadata are usually not exported, so those render as `unknown` instead of failing.

## Dependency install without system pip/venv

If the host blocks system-wide installs or lacks `python3-venv`, install dependencies into the repo-local vendor folder instead:

```bash
python skills/flight-search/scripts/install_local_deps.py
```

That installer prefers `skills/flight-search/requirements.txt`, falls back to the repo root `requirements.txt`, and installs into `skills/flight-search/vendor/`.
The helper module/CLI automatically imports from there.

## Contents

The skill teaches how to use:

- the packaged helper API under `skills/flight-search/base/`
- the skill-local dependency file at `skills/flight-search/requirements.txt`
- the CLI wrapper at `skills/flight-search/scripts/flight_search_base.py`
- the runnable example at `skills/flight-search/examples/example_runner.py`
- compatibility fallback from published `fast-flights` rc0 to the newer source API shape

It includes examples such as:

- evening flights
- only Airbus flights
- only flights below 8k
- combined filters like Airbus + below 8k + after 4pm
