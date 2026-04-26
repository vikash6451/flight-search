from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys

import pytest

SKILL_ROOT = Path(__file__).resolve().parents[1] / "skills" / "flight-search"
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

from base import api


def _sample_letsfg_payload():
    return {
        "total_results": 1,
        "offers": [
            {
                "id": "ct_123",
                "price": 9312,
                "currency": "INR",
                "price_normalized": 9312,
                "airlines": ["SG"],
                "source": "cleartrip_ota",
                "booking_url": "https://www.cleartrip.com/flights/results",
                "outbound": {
                    "stopovers": 0,
                    "total_duration_seconds": 11100,
                    "segments": [
                        {
                            "airline": "SG",
                            "flight_no": "SG199",
                            "origin": "DEL",
                            "destination": "BLR",
                            "departure": "2026-04-30T11:55:00",
                            "arrival": "2026-04-30T15:00:00",
                            "duration_seconds": 11100,
                            "aircraft": "Boeing 737",
                        }
                    ],
                },
            }
        ],
    }


def test_letsfg_is_used_as_fallback_when_google_provider_crashes(monkeypatch):
    def crash_google(params):
        raise IndexError("list index out of range")

    monkeypatch.setattr(api, "_search_google_provider", crash_google)
    monkeypatch.setattr(api, "_run_letsfg_search", lambda params, limit: _sample_letsfg_payload())

    response = api.search_flights_with_filters(
        api.FlightSearchParams(
            origin="DEL",
            destination="BLR",
            date="2026-04-30",
            currency="INR",
            max_results=5,
            sources=("google-flights", "letsfg"),
        )
    )

    assert response.errors["google-flights"].startswith("IndexError")
    assert len(response.results) == 1
    result = response.results[0]
    assert result.source == "letsfg:cleartrip_ota"
    assert result.price == 9312
    assert result.currency == "INR"
    assert result.segments[0].flight_number == "SG199"


def test_letsfg_enriches_when_google_returns_fewer_than_max_results(monkeypatch):
    google = api.NormalizedItinerary(
        source="google-flights",
        source_label="Google Flights",
        price=9500,
        currency="INR",
        airlines=("AI",),
        departure_at=datetime(2026, 4, 30, 1, 30),
        arrival_at=datetime(2026, 4, 30, 4, 25),
        duration_minutes=175,
        stop_count=0,
        booking_url="https://google.com/travel/flights",
        segments=(
            api.NormalizedSegment(
                origin_code="DEL",
                origin_name="Delhi Airport",
                destination_code="BLR",
                destination_name="Bengaluru Airport",
                departure_at=datetime(2026, 4, 30, 1, 30),
                arrival_at=datetime(2026, 4, 30, 4, 25),
                duration_minutes=175,
                plane_type="",
                flight_number="AI2815",
            ),
        ),
        raw=None,
    )

    monkeypatch.setattr(
        api,
        "_search_google_provider",
        lambda params: api.SearchResponse(results=(google,), raw=["google"], mode="legacy_rc0"),
    )
    monkeypatch.setattr(api, "_run_letsfg_search", lambda params, limit: _sample_letsfg_payload())

    response = api.search_flights_with_filters(
        api.FlightSearchParams(
            origin="DEL",
            destination="BLR",
            date="2026-04-30",
            currency="INR",
            max_results=5,
            sources=("google-flights", "letsfg"),
        )
    )

    assert [item.source for item in response.results] == ["letsfg:cleartrip_ota", "google-flights"]
    assert response.results[0].price < response.results[1].price


def test_malformed_legacy_google_price_rows_are_skipped():
    assert api._legacy_price_from_row([[], "opaque-token"]) is None
    assert api._legacy_price_from_row([[None], "opaque-token"]) is None
    assert api._legacy_price_from_row([[None, 7859], "opaque-token"]) == 7859
