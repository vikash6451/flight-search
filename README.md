# flight-search-skill

A Claude/Codex-style skill pack for searching flights through the `fast_flights` wrapper with:

- user-friendly itinerary formatting
- price filters
- aircraft-family filters
- time-window filters
- date-window search examples
- an included base helper script/API wrapper

## Layout

```text
skills/
  flight-search/
    SKILL.md
    references/
      setup.md
    scripts/
      flight_search_base.py
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

## Contents

The skill teaches how to use:

- `find_flights(...)`
- `format_itineraries(...)`
- `SearchRequest`
- `search_flights(...)`
- `search_date_window(...)`

It includes examples such as:

- evening flights
- only Airbus flights
- only flights below 8k
- combined filters like Airbus + below 8k + after 4pm
