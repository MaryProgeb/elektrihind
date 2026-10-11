"""Elering Live price fetch for one Europe/Tallinn calendar day."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

ELERING_URL = "https://dashboard.elering.ee/api/nps/price"
INTERVAL = timedelta(minutes=15)
DEFAULT_TIMEOUT = 15.0


class PricesUnavailable(Exception):
    """The requested day has no usable Estonian price series."""


@dataclass(frozen=True)
class Interval:
    """One 15-minute Nord Pool EE product. Price is EUR/MWh excluding VAT."""

    start: datetime  # timezone-aware, in the requested local timezone
    price_eur_mwh: float


HttpGet = Callable[[str], bytes]


def _default_http_get(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=DEFAULT_TIMEOUT) as resp:
        return resp.read()


def day_window_utc(day: date, tz: ZoneInfo) -> tuple[datetime, datetime]:
    """UTC instants of local midnight at the start of `day` and of the next day."""
    start_local = datetime(day.year, day.month, day.day, tzinfo=tz)
    next_day = day + timedelta(days=1)
    end_local = datetime(next_day.year, next_day.month, next_day.day, tzinfo=tz)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)


def build_url(day: date, tz: ZoneInfo) -> str:
    start_utc, end_utc = day_window_utc(day, tz)
    query = urllib.parse.urlencode(
        {
            "start": start_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "end": end_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
    )
    return f"{ELERING_URL}?{query}"


def parse_ee_day(body: bytes, day: date, tz: ZoneInfo) -> list[Interval]:
    """Parse an Elering payload and return the EE intervals that start on `day` (local).

    Raises PricesUnavailable for unsuccessful payloads, a missing or empty `data.ee`,
    malformed rows, or no intervals that fall on `day`.
    """
    try:
        payload = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PricesUnavailable("response is not valid JSON") from exc

    if not isinstance(payload, dict) or payload.get("success") is not True:
        raise PricesUnavailable("Elering reported an unsuccessful payload")

    data = payload.get("data")
    rows = data.get("ee") if isinstance(data, dict) else None
    if not rows:
        raise PricesUnavailable("no EE intervals in response")

    intervals: list[Interval] = []
    try:
        for row in rows:
            start = datetime.fromtimestamp(int(row["timestamp"]), tz)
            price = float(row["price"])
            if start.date() == day:
                intervals.append(Interval(start=start, price_eur_mwh=price))
    except (KeyError, TypeError, ValueError, OverflowError, OSError) as exc:
        raise PricesUnavailable("malformed EE interval in response") from exc

    if not intervals:
        raise PricesUnavailable(f"no EE intervals start on {day.isoformat()}")

    intervals.sort(key=lambda iv: iv.start)
    return intervals


def fetch_day_prices(
    day: date,
    tz: ZoneInfo,
    *,
    http_get: HttpGet | None = None,
) -> list[Interval]:
    """Fetch EE 15-minute prices for `day` (local calendar day in `tz`).

    Only `day` is requested; the next day is never fetched. Transport failures
    and bad payloads raise PricesUnavailable.
    """
    get = http_get or _default_http_get
    url = build_url(day, tz)
    try:
        body = get(url)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise PricesUnavailable(f"Elering request failed: {exc}") from exc
    return parse_ee_day(body, day, tz)
