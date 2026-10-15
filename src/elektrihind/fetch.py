"""Elering Live price fetch for Europe/Tallinn calendar date ranges."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
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
    return _build_url(*day_window_utc(day, tz))


def date_range_window_utc(first_day: date, last_day: date, tz: ZoneInfo) -> tuple[datetime, datetime]:
    """UTC instants spanning both local dates, inclusive."""
    if last_day < first_day:
        raise ValueError("last_day must not be before first_day")
    start_utc, _ = day_window_utc(first_day, tz)
    _, end_utc = day_window_utc(last_day, tz)
    return start_utc, end_utc


def _build_url(start_utc: datetime, end_utc: datetime) -> str:
    query = urllib.parse.urlencode(
        {
            "start": start_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "end": end_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
    )
    return f"{ELERING_URL}?{query}"


def build_range_url(first_day: date, last_day: date, tz: ZoneInfo) -> str:
    """Build an Elering request for inclusive local dates, expressed as UTC bounds."""
    return _build_url(*date_range_window_utc(first_day, last_day, tz))


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


def parse_ee_date_range(
    body: bytes,
    first_day: date,
    last_day: date,
    tz: ZoneInfo,
) -> list[Interval]:
    """Parse EE intervals whose local start date is within an inclusive date range."""
    if last_day < first_day:
        raise ValueError("last_day must not be before first_day")
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
            if first_day <= start.date() <= last_day:
                intervals.append(Interval(start=start, price_eur_mwh=price))
    except (KeyError, TypeError, ValueError, OverflowError, OSError) as exc:
        raise PricesUnavailable("malformed EE interval in response") from exc

    if not intervals:
        raise PricesUnavailable(
            f"no EE intervals start between {first_day.isoformat()} and {last_day.isoformat()}"
        )

    intervals.sort(key=lambda iv: iv.start.timestamp())
    return intervals


def validate_complete_day(intervals: list[Interval], day: date, tz: ZoneInfo) -> None:
    """Raise PricesUnavailable unless `day` has exactly one value per 15m start."""
    start = datetime.combine(day, time.min, tzinfo=tz).timestamp()
    end = datetime.combine(day + timedelta(days=1), time.min, tzinfo=tz).timestamp()
    expected = set(range(int(start), int(end), int(INTERVAL.total_seconds())))
    counts = Counter(
        iv.start.timestamp()
        for iv in intervals
        if iv.start.astimezone(tz).date() == day
    )
    if set(counts) != expected or any(count != 1 for count in counts.values()):
        raise PricesUnavailable(
            f"EE series for {day.isoformat()} is incomplete or contains duplicate intervals"
        )


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


def fetch_date_range_prices(
    first_day: date,
    last_day: date,
    tz: ZoneInfo,
    *,
    http_get: HttpGet | None = None,
) -> list[Interval]:
    """Fetch EE prices for inclusive local dates in one Elering request."""
    get = http_get or _default_http_get
    url = build_range_url(first_day, last_day, tz)
    try:
        body = get(url)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise PricesUnavailable(f"Elering request failed: {exc}") from exc
    return parse_ee_date_range(body, first_day, last_day, tz)
