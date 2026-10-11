from datetime import date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from elektrihind.fetch import Interval
from elektrihind.slots import candidate_windows, ceil_to_interval, remaining_day_cutoff

TZ = ZoneInfo("Europe/Tallinn")
TODAY = date(2026, 10, 11)


def series(start_local: datetime, prices: list[float]) -> list[Interval]:
    base = start_local.timestamp()
    return [
        Interval(start=datetime.fromtimestamp(base + 900 * i, TZ), price_eur_mwh=p)
        for i, p in enumerate(prices)
    ]


def full_day(day: date = TODAY, price: float = 50.0) -> list[Interval]:
    start = datetime(day.year, day.month, day.day, tzinfo=TZ)
    return series(start, [price] * 96)


def starts(windows) -> list[str]:
    return [w.start.strftime("%Y-%m-%d %H:%M") for w in windows]


# --- cutoff -----------------------------------------------------------------


def test_run_before_8_uses_0800_cutoff():
    now = datetime(2026, 10, 11, 7, 0, tzinfo=TZ)
    assert remaining_day_cutoff(now, TODAY) == datetime(2026, 10, 11, 8, 0, tzinfo=TZ)


def test_interval_at_0745_is_not_eligible_for_0800_cutoff():
    now = datetime(2026, 10, 11, 7, 0, tzinfo=TZ)
    cutoff = remaining_day_cutoff(now, TODAY)
    windows = candidate_windows(full_day(), cutoff)
    assert windows[0].start.strftime("%H:%M") == "08:00"
    assert all(w.start >= cutoff for w in windows)


def test_interval_at_cutoff_is_eligible():
    now = datetime(2026, 10, 11, 8, 0, tzinfo=TZ)
    cutoff = remaining_day_cutoff(now, TODAY)
    assert cutoff == datetime(2026, 10, 11, 8, 0, tzinfo=TZ)
    windows = candidate_windows(full_day(), cutoff)
    assert windows[0].start == datetime(2026, 10, 11, 8, 0, tzinfo=TZ)


def test_late_run_excludes_interval_that_already_started():
    # Run at 08:20: the 08:15 product started before the run, so the cutoff is 08:30.
    now = datetime(2026, 10, 11, 8, 20, tzinfo=TZ)
    cutoff = remaining_day_cutoff(now, TODAY)
    assert cutoff == datetime(2026, 10, 11, 8, 30, tzinfo=TZ)

    windows = candidate_windows(full_day(), cutoff)
    assert windows[0].start == datetime(2026, 10, 11, 8, 30, tzinfo=TZ)
    assert not any(w.start.strftime("%H:%M") == "08:15" for w in windows)


def test_run_exactly_on_a_boundary_keeps_that_interval():
    assert ceil_to_interval(datetime(2026, 10, 11, 8, 30, tzinfo=TZ)) == datetime(
        2026, 10, 11, 8, 30, tzinfo=TZ
    )


def test_earliest_start_moves_cutoff_later():
    now = datetime(2026, 10, 11, 8, 0, tzinfo=TZ)
    cutoff = remaining_day_cutoff(now, TODAY, earliest_start=time(9, 30))
    assert cutoff == datetime(2026, 10, 11, 9, 30, tzinfo=TZ)


def test_earliest_start_does_not_pull_cutoff_before_run_time():
    now = datetime(2026, 10, 11, 8, 20, tzinfo=TZ)
    cutoff = remaining_day_cutoff(now, TODAY, earliest_start=time(8, 0))
    assert cutoff == datetime(2026, 10, 11, 8, 30, tzinfo=TZ)


# --- window shape -----------------------------------------------------------


def test_window_is_twelve_intervals_three_hours_long():
    windows = candidate_windows(full_day(), datetime(2026, 10, 11, 8, 0, tzinfo=TZ))
    first = windows[0]
    assert first.end - first.start == timedelta(hours=3)


def test_window_mean_is_exact_average_of_twelve_prices():
    prices = [float(p) for p in range(1, 13)]  # 1..12 -> mean 6.5
    start = datetime(2026, 10, 11, 8, 0, tzinfo=TZ)
    windows = candidate_windows(series(start, prices), start)
    assert len(windows) == 1
    assert windows[0].mean_eur_mwh == Decimal("6.5")


def test_no_midnight_wrap():
    # Today's intervals plus tomorrow's; windows that cross 00:00 must be dropped.
    today = full_day(TODAY)
    tomorrow = full_day(date(2026, 10, 12))
    cutoff = datetime(2026, 10, 11, 8, 0, tzinfo=TZ)
    windows = candidate_windows(today + tomorrow, cutoff)

    today_starts = [w.start for w in windows if w.start.date() == TODAY]
    # 21:00 is the latest start whose 12 products all begin today (last product 23:45,
    # window ends exactly at midnight). 21:15 would need the 00:00 product -> dropped.
    assert max(today_starts).strftime("%H:%M") == "21:00"
    assert "2026-10-11 21:15" not in starts(windows)
    assert all(w.start.date() == w.end.date() or w.end.strftime("%H:%M") == "00:00"
               for w in windows)


def test_gap_in_series_breaks_windows():
    intervals = full_day()
    del intervals[40]  # remove 10:00 product
    cutoff = datetime(2026, 10, 11, 8, 0, tzinfo=TZ)
    windows = candidate_windows(intervals, cutoff)
    for w in windows:
        assert not (w.start <= datetime(2026, 10, 11, 10, 0, tzinfo=TZ) < w.end)


def test_latest_end_drops_window_ending_after_bound():
    cutoff = datetime(2026, 10, 11, 8, 0, tzinfo=TZ)
    windows = candidate_windows(full_day(), cutoff, latest_end=time(22, 0))
    names = starts(windows)

    assert "2026-10-11 19:00" in names  # ends exactly 22:00 -> eligible
    assert "2026-10-11 19:15" not in names  # ends 22:15 -> not eligible
    assert all(w.end.strftime("%H:%M") <= "22:00" for w in windows if w.start.date() == TODAY)


def test_dst_23h_day_window_is_three_real_hours():
    start = datetime(2026, 3, 29, 0, 0, tzinfo=TZ)
    prices = [50.0] * 92
    intervals = series(start, prices)  # 23h day: 92 products
    windows = candidate_windows(intervals, start)
    first = windows[0]
    # Wall-clock subtraction on a shared tzinfo would give 4h here; compare real instants.
    assert first.end.timestamp() - first.start.timestamp() == 3 * 3600
    assert first.end.strftime("%H:%M") == "04:00"  # 00:00 EET + 3h real = 04:00 EEST
