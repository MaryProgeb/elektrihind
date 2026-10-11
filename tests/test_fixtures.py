import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
TALLINN = ZoneInfo("Europe/Tallinn")


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def test_24h_day_is_elering_shaped_with_96_intervals_on_one_local_day():
    payload = load("elering_ee_24h.json")
    assert payload["success"] is True
    ee = payload["data"]["ee"]
    assert len(ee) == 96

    first = datetime.fromtimestamp(ee[0]["timestamp"], TALLINN)
    last = datetime.fromtimestamp(ee[-1]["timestamp"], TALLINN)
    assert first.date() == last.date()
    assert first.strftime("%H:%M") == "00:00"
    assert last.strftime("%H:%M") == "23:45"


def test_24h_intervals_are_900_seconds_apart_and_prices_are_numbers():
    ee = load("elering_ee_24h.json")["data"]["ee"]
    for prev, cur in zip(ee, ee[1:]):
        assert cur["timestamp"] - prev["timestamp"] == 900
    assert all(isinstance(row["price"], (int, float)) for row in ee)


def test_24h_fixture_contains_a_negative_price():
    ee = load("elering_ee_24h.json")["data"]["ee"]
    assert any(row["price"] < 0 for row in ee)


def test_24h_fixture_includes_other_market_that_parser_must_ignore():
    data = load("elering_ee_24h.json")["data"]
    assert "fi" in data and data["fi"]


@pytest.mark.parametrize(
    "name, expected_seconds",
    [("elering_ee_dst_23h.json", 23 * 3600), ("elering_ee_dst_25h.json", 25 * 3600)],
)
def test_dst_fixtures_span_real_elapsed_hours(name, expected_seconds):
    ee = load(name)["data"]["ee"]
    span = ee[-1]["timestamp"] + 900 - ee[0]["timestamp"]
    assert span == expected_seconds
    assert len(ee) == expected_seconds // 900
    for prev, cur in zip(ee, ee[1:]):
        assert cur["timestamp"] - prev["timestamp"] == 900


def test_empty_fixture_has_success_and_no_ee_intervals():
    payload = load("elering_ee_empty.json")
    assert payload["success"] is True
    assert payload["data"]["ee"] == []


def test_unsuccessful_fixture_is_not_success():
    payload = load("elering_unsuccessful.json")
    assert payload["success"] is False
