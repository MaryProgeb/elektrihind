"""Window scoring and greedy 3-slot selection over a remaining-day price series."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal

from elektrihind.fetch import INTERVAL, Interval

SLOT_INTERVALS = 12  # 12 x 15 min = 3 hours
SELECT_COUNT = 3  # dishwasher windows per daily message
SLOT_LENGTH = INTERVAL * SLOT_INTERVALS
DAY_START = time(8, 0)  # remaining-day search starts at 08:00 local
INTERVAL_SECONDS = int(INTERVAL.total_seconds())


@dataclass(frozen=True)
class Window:
    """A candidate 3-hour dishwasher window.

    `mean_eur_mwh` is the exact mean of the 12 source prices (EUR/MWh, excl. VAT).
    Ranking uses this value; VAT conversion happens only for display.
    """

    start: datetime  # aware, local tz; start of the first interval
    end: datetime  # start + 3 hours
    mean_eur_mwh: Decimal


def ceil_to_interval(moment: datetime) -> datetime:
    """Smallest 15-minute boundary >= moment, computed on the epoch so DST is handled."""
    boundary = math.ceil(moment.timestamp() / INTERVAL_SECONDS) * INTERVAL_SECONDS
    return datetime.fromtimestamp(boundary, moment.tzinfo)


def remaining_day_cutoff(
    now: datetime,
    day: date,
    *,
    earliest_start: time | None = None,
    day_start: time = DAY_START,
) -> datetime:
    """First instant that may begin a slot in the remaining-day search.

    The cutoff is the latest of:
      - `now` rounded up to the next 15-minute boundary (an interval that already
        started before `now` is excluded; one starting exactly at `now` is kept),
      - 08:00 local on `day`,
      - `earliest_start` on `day`, if configured.
    """
    tz = now.tzinfo
    cutoff = max(ceil_to_interval(now), datetime.combine(day, day_start, tzinfo=tz))
    if earliest_start is not None:
        cutoff = max(cutoff, datetime.combine(day, earliest_start, tzinfo=tz))
    return cutoff


def candidate_windows(
    intervals: Sequence[Interval],
    cutoff: datetime,
    *,
    latest_end: time | None = None,
) -> list[Window]:
    """All eligible 12-interval windows, in start order.

    A window is eligible when:
      - every interval starts at or after `cutoff`,
      - its 12 intervals are consecutive 15-minute instants (no gaps),
      - all of its intervals start on the same local calendar day (no midnight wrap),
      - if `latest_end` is set, it ends at or before that local time on the same day.
    Windows are not de-duplicated or de-overlapped here; see select_three.
    """
    # Compare by epoch seconds: aware datetimes sharing a tzinfo compare wall-clock,
    # which is wrong during the repeated hour of a DST fall-back.
    cutoff_ts = cutoff.timestamp()
    eligible = sorted(
        (iv for iv in intervals if iv.start.timestamp() >= cutoff_ts),
        key=lambda iv: iv.start.timestamp(),
    )
    windows: list[Window] = []
    for i in range(len(eligible) - SLOT_INTERVALS + 1):
        group = eligible[i : i + SLOT_INTERVALS]
        first = group[0]
        last = group[-1]

        if not _is_contiguous(group):
            continue
        if last.start.date() != first.start.date():
            continue

        end = datetime.fromtimestamp(
            first.start.timestamp() + SLOT_LENGTH.total_seconds(), first.start.tzinfo
        )
        if latest_end is not None:
            if end.date() != first.start.date() or end.time() > latest_end:
                continue

        total = sum((Decimal(str(iv.price_eur_mwh)) for iv in group), Decimal(0))
        windows.append(
            Window(start=first.start, end=end, mean_eur_mwh=total / SLOT_INTERVALS)
        )
    return windows


def select_three(windows: Sequence[Window], count: int = SELECT_COUNT) -> list[Window]:
    """Greedy pick of up to `count` non-overlapping windows, cheapest first.

    Ranks by mean EUR/MWh ascending, then earlier start. Takes the cheapest, skips any
    later candidate that shares an interval with a chosen window, and repeats.
    Returns fewer than `count` windows if not enough non-overlapping ones exist.
    """
    ranked = sorted(windows, key=lambda w: (w.mean_eur_mwh, w.start.timestamp()))
    chosen: list[Window] = []
    for candidate in ranked:
        if len(chosen) == count:
            break
        if any(_overlaps(candidate, picked) for picked in chosen):
            continue
        chosen.append(candidate)
    return chosen


def _overlaps(a: Window, b: Window) -> bool:
    """True if the two windows share at least one 15-minute interval."""
    return a.start.timestamp() < b.end.timestamp() and b.start.timestamp() < a.end.timestamp()


def _is_contiguous(group: Sequence[Interval]) -> bool:
    return all(
        cur.start.timestamp() - prev.start.timestamp() == INTERVAL_SECONDS
        for prev, cur in zip(group, group[1:])
    )
