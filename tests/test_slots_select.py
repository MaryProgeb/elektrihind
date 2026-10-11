from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from elektrihind.fetch import Interval
from elektrihind.slots import Window, candidate_windows, select_three

TZ = ZoneInfo("Europe/Tallinn")
TODAY = date(2026, 10, 11)
DAY_START = datetime(2026, 10, 11, 0, 0, tzinfo=TZ)


def series(prices: list[float], start: datetime = DAY_START) -> list[Interval]:
    base = start.timestamp()
    return [
        Interval(start=datetime.fromtimestamp(base + 900 * i, TZ), price_eur_mwh=p)
        for i, p in enumerate(prices)
    ]


def windows_for(prices: list[float], cutoff: datetime = DAY_START) -> list[Window]:
    return candidate_windows(series(prices), cutoff)


def hhmm(windows) -> list[str]:
    return [w.start.strftime("%H:%M") for w in windows]


def assert_no_overlap(windows: list[Window]) -> None:
    for i, a in enumerate(windows):
        for b in windows[i + 1 :]:
            disjoint = a.end.timestamp() <= b.start.timestamp() or b.end.timestamp() <= a.start.timestamp()
            assert disjoint, f"{a.start} overlaps {b.start}"


def test_three_cheapest_non_overlapping_windows_are_returned_cheapest_first():
    # 96 products at 100 EUR/MWh with three cheap 12-product blocks.
    prices = [100.0] * 96
    for i in range(4, 16):
        prices[i] = 10.0  # 01:00-04:00
    for i in range(28, 40):
        prices[i] = 20.0  # 07:00-10:00
    for i in range(52, 64):
        prices[i] = 30.0  # 13:00-16:00

    chosen = select_three(windows_for(prices))

    assert hhmm(chosen) == ["01:00", "07:00", "13:00"]
    assert [w.mean_eur_mwh for w in chosen] == [Decimal(10), Decimal(20), Decimal(30)]
    assert_no_overlap(chosen)


def test_tie_on_mean_prefers_earlier_start():
    flat = [50.0] * 96  # every window has mean 50
    chosen = select_three(windows_for(flat))

    assert hhmm(chosen) == ["00:00", "03:00", "06:00"]


def test_overlapping_window_is_discarded_after_a_cheaper_pick():
    # Cheapest block 11:00-14:00 (products 44..55). Window 12:00-15:00 (start 48)
    # is cheaper than most, but shares 12:00-14:00 with the pick, so it must be dropped.
    prices = [100.0] * 96
    for i in range(44, 56):
        prices[i] = 10.0
    chosen = select_three(windows_for(prices))

    assert chosen[0].start.strftime("%H:%M") == "11:00"
    assert "12:00" not in hhmm(chosen)
    assert "10:00" not in hhmm(chosen)  # 10:00-13:00 also overlaps 11:00-14:00
    assert_no_overlap(chosen)


def test_short_remaining_day_returns_empty():
    # Only 11 products after cutoff: not enough for one 12-product window.
    chosen = select_three(windows_for([50.0] * 11))
    assert chosen == []


def test_exactly_twelve_products_returns_one_window():
    chosen = select_three(windows_for([50.0] * 12))
    assert hhmm(chosen) == ["00:00"]


def test_only_two_windows_fit_returns_two():
    # 30 products (7.5 h) can hold at most two non-overlapping 12-product windows.
    # Cheapest block at products 6..17 (01:30-04:30); second block 18..29 (04:30-07:30).
    # After picking 6..17, only a start of 18 can fit, so the result is exactly two.
    prices = [100.0] * 30
    for i in range(6, 18):
        prices[i] = 10.0
    for i in range(18, 30):
        prices[i] = 20.0

    chosen = select_three(windows_for(prices))

    assert hhmm(chosen) == ["01:30", "04:30"]
    assert_no_overlap(chosen)


def test_selection_is_cheapest_first_and_never_exceeds_three():
    prices = [float(20 + (i * 37) % 80) for i in range(96)]
    chosen = select_three(windows_for(prices))

    assert len(chosen) == 3
    means = [w.mean_eur_mwh for w in chosen]
    assert means == sorted(means)
    assert_no_overlap(chosen)


def test_selection_respects_cutoff():
    prices = [100.0] * 96
    for i in range(20, 32):  # 05:00-08:00 cheap block
        prices[i] = 1.0
    cutoff = datetime(2026, 10, 11, 8, 0, tzinfo=TZ)

    chosen = select_three(windows_for(prices, cutoff))

    assert all(w.start >= cutoff for w in chosen)
    assert "05:00" not in hhmm(chosen)


def test_window_end_is_three_hours_after_start():
    chosen = select_three(windows_for([50.0] * 96))
    for w in chosen:
        assert w.end - w.start == timedelta(hours=3)
