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

## Dependency install without system pip/venv

If the host blocks system-wide installs or lacks `python3-venv`, install dependencies into the repo-local vendor folder instead:

```bash
python skills/flight-search/scripts/install_local_deps.py
```

That installer prefers `skills/flight-search/requirements.txt`, falls back to the repo root `requirements.txt`, and installs into `skills/flight-search/vendor/`.
The helper module/CLI automatically imports from there.

## Contents

The skill teaches how to use:

- `find_flights(...)`
- `format_itineraries(...)`
- `SearchRequest`
- `search_flights(...)`
- `search_date_window(...)`
- the packaged helper API under `skills/flight-search/base/`
- the skill-local dependency file at `skills/flight-search/requirements.txt`
- the CLI wrapper at `skills/flight-search/scripts/flight_search_base.py`
- the runnable example at `skills/flight-search/examples/example_runner.py`

It includes examples such as:

- evening flights
- only Airbus flights
- only flights below 8k
- combined filters like Airbus + below 8k + after 4pm
