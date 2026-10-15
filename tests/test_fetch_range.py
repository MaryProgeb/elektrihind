import json
from datetime import date, datetime, time, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

import pytest

from elektrihind.fetch import (
    PricesUnavailable,
    date_range_window_utc,
    fetch_date_range_prices,
    validate_complete_day,
)

TZ = ZoneInfo("Europe/Tallinn")
FIXTURES = Path(__file__).parent / "fixtures"


def fixture_bytes(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def make_rows(day: date) -> list[dict[str, int | float]]:
    start = datetime.combine(day, time.min, tzinfo=TZ).timestamp()
    end = datetime.combine(day + timedelta(days=1), time.min, tzinfo=TZ).timestamp()
    return [
        {"timestamp": int(ts), "price": 50.0}
        for ts in range(int(start), int(end), 900)
    ]


def payload(rows) -> bytes:
    return json.dumps({"success": True, "data": {"ee": rows}}).encode()


def get_returning(body: bytes):
    calls: list[str] = []

    def get(url: str) -> bytes:
        calls.append(url)
        return body

    get.calls = calls
    return get


def test_range_request_uses_utc_midnights_for_both_inclusive_dates():
    get = get_returning(payload(make_rows(date(2026, 10, 11))))

    intervals = fetch_date_range_prices(date(2026, 10, 10), date(2026, 10, 11), TZ, http_get=get)

    assert len(intervals) == 96
    query = parse_qs(urlparse(get.calls[0]).query)
    assert query["start"] == ["2026-10-09T21:00:00Z"]
    assert query["end"] == ["2026-10-11T21:00:00Z"]


def test_range_filters_intervals_to_both_requested_local_dates():
    rows = make_rows(date(2026, 10, 10)) + make_rows(date(2026, 10, 11))
    rows += make_rows(date(2026, 10, 12))
    # Include a row from the preceding date too.
    rows = make_rows(date(2026, 10, 9))[-1:] + rows

    intervals = fetch_date_range_prices(
        date(2026, 10, 10), date(2026, 10, 11), TZ, http_get=get_returning(payload(rows))
    )

    assert len(intervals) == 192
    assert {iv.start.date() for iv in intervals} == {date(2026, 10, 10), date(2026, 10, 11)}


@pytest.mark.parametrize(
    ("day", "fixture", "expected_count"),
    [
        (date(2026, 3, 29), "elering_ee_dst_23h.json", 92),
        (date(2026, 10, 11), "elering_ee_24h.json", 96),
        (date(2026, 10, 25), "elering_ee_dst_25h.json", 100),
    ],
)
def test_complete_series_fixtures_cover_dst_day_lengths(day, fixture, expected_count):
    intervals = fetch_date_range_prices(
        day - timedelta(days=1), day, TZ, http_get=get_returning(fixture_bytes(fixture))
    )

    validate_complete_day(intervals, day, TZ)
    assert len(intervals) == expected_count


@pytest.mark.parametrize(
    ("first_day", "last_day", "expected_hours"),
    [
        (date(2026, 3, 28), date(2026, 3, 29), 47),
        (date(2026, 10, 24), date(2026, 10, 25), 49),
    ],
)
def test_local_date_range_window_accounts_for_dst_length(first_day, last_day, expected_hours):
    start, end = date_range_window_utc(first_day, last_day, TZ)
    assert (end - start).total_seconds() == expected_hours * 3600


def test_missing_tomorrow_is_unavailable_even_when_today_is_present():
    today = date(2026, 10, 11)
    intervals = fetch_date_range_prices(
        today,
        today + timedelta(days=1),
        TZ,
        http_get=get_returning(fixture_bytes("elering_ee_24h.json")),
    )

    with pytest.raises(PricesUnavailable, match="incomplete or contains duplicate"):
        validate_complete_day(intervals, today + timedelta(days=1), TZ)


def test_partial_tomorrow_is_unavailable():
    rows = json.loads(fixture_bytes("elering_ee_24h.json"))["data"]["ee"][:-1]
    intervals = fetch_date_range_prices(
        date(2026, 10, 10), date(2026, 10, 11), TZ, http_get=get_returning(payload(rows))
    )

    with pytest.raises(PricesUnavailable, match="incomplete or contains duplicate"):
        validate_complete_day(intervals, date(2026, 10, 11), TZ)


def test_duplicate_tomorrow_interval_is_unavailable():
    rows = json.loads(fixture_bytes("elering_ee_24h.json"))["data"]["ee"]
    rows.append(rows[-1])
    intervals = fetch_date_range_prices(
        date(2026, 10, 10), date(2026, 10, 11), TZ, http_get=get_returning(payload(rows))
    )

    with pytest.raises(PricesUnavailable, match="incomplete or contains duplicate"):
        validate_complete_day(intervals, date(2026, 10, 11), TZ)
