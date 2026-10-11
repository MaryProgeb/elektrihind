import json
import urllib.error
from datetime import date
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

import pytest

from elektrihind.fetch import (
    ELERING_URL,
    PricesUnavailable,
    build_url,
    day_window_utc,
    fetch_day_prices,
)

TALLINN = ZoneInfo("Europe/Tallinn")
FIXTURES = Path(__file__).parent / "fixtures"
TODAY = date(2026, 10, 11)


def fixture_bytes(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def fake_get(body: bytes):
    calls: list[str] = []

    def get(url: str) -> bytes:
        calls.append(url)
        return body

    get.calls = calls  # type: ignore[attr-defined]
    return get


def test_success_returns_ee_intervals_for_the_day():
    get = fake_get(fixture_bytes("elering_ee_24h.json"))

    intervals = fetch_day_prices(TODAY, TALLINN, http_get=get)

    assert len(intervals) == 96
    assert intervals[0].start.strftime("%Y-%m-%d %H:%M") == "2026-10-11 00:00"
    assert intervals[-1].start.strftime("%H:%M") == "23:45"
    assert all(iv.start.tzinfo is not None for iv in intervals)
    assert all(isinstance(iv.price_eur_mwh, float) for iv in intervals)


def test_other_markets_in_payload_are_ignored():
    # The 24h fixture also carries a "fi" series; only "ee" may be used.
    get = fake_get(fixture_bytes("elering_ee_24h.json"))

    intervals = fetch_day_prices(TODAY, TALLINN, http_get=get)

    assert len(intervals) == 96
    assert 48.31 not in [iv.price_eur_mwh for iv in intervals]


def test_empty_ee_is_unavailable():
    get = fake_get(fixture_bytes("elering_ee_empty.json"))

    with pytest.raises(PricesUnavailable, match="no EE intervals"):
        fetch_day_prices(TODAY, TALLINN, http_get=get)


def test_unsuccessful_payload_is_unavailable():
    get = fake_get(fixture_bytes("elering_unsuccessful.json"))

    with pytest.raises(PricesUnavailable, match="unsuccessful"):
        fetch_day_prices(TODAY, TALLINN, http_get=get)


def test_transport_failure_is_unavailable():
    def boom(url: str) -> bytes:
        raise urllib.error.URLError("network down")

    with pytest.raises(PricesUnavailable, match="request failed"):
        fetch_day_prices(TODAY, TALLINN, http_get=boom)


def test_timeout_is_unavailable():
    def slow(url: str) -> bytes:
        raise TimeoutError("timed out")

    with pytest.raises(PricesUnavailable):
        fetch_day_prices(TODAY, TALLINN, http_get=slow)


def test_non_json_body_is_unavailable():
    with pytest.raises(PricesUnavailable, match="JSON"):
        fetch_day_prices(TODAY, TALLINN, http_get=fake_get(b"<html>oops</html>"))


def test_malformed_row_is_unavailable():
    body = json.dumps({"success": True, "data": {"ee": [{"timestamp": 1}]}}).encode()

    with pytest.raises(PricesUnavailable, match="malformed"):
        fetch_day_prices(TODAY, TALLINN, http_get=fake_get(body))


def test_request_window_is_today_only_in_utc():
    get = fake_get(fixture_bytes("elering_ee_24h.json"))

    fetch_day_prices(TODAY, TALLINN, http_get=get)

    (url,) = get.calls
    assert url.startswith(ELERING_URL + "?")
    query = parse_qs(urlparse(url).query)
    # 2026-10-11 00:00 EEST (UTC+3) -> 2026-10-10 21:00Z ; next midnight -> 2026-10-11 21:00Z
    assert query["start"] == ["2026-10-10T21:00:00Z"]
    assert query["end"] == ["2026-10-11T21:00:00Z"]


def test_dst_day_window_spans_real_hours():
    start, end = day_window_utc(date(2026, 3, 29), TALLINN)
    assert (end - start).total_seconds() == 23 * 3600

    start, end = day_window_utc(date(2026, 10, 25), TALLINN)
    assert (end - start).total_seconds() == 25 * 3600


def test_build_url_uses_utc_z_suffix():
    url = build_url(TODAY, TALLINN)
    assert "start=2026-10-10T21%3A00%3A00Z" in url
    assert url.startswith("https://dashboard.elering.ee/api/nps/price?")


def test_dst_23h_day_returns_92_intervals():
    get = fake_get(fixture_bytes("elering_ee_dst_23h.json"))

    intervals = fetch_day_prices(date(2026, 3, 29), TALLINN, http_get=get)

    assert len(intervals) == 92


def test_dst_25h_day_returns_100_intervals():
    get = fake_get(fixture_bytes("elering_ee_dst_25h.json"))

    intervals = fetch_day_prices(date(2026, 10, 25), TALLINN, http_get=get)

    assert len(intervals) == 100
