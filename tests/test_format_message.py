from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from elektrihind.fetch import Interval
from elektrihind.format import format_daily_message, format_window_range
from elektrihind.slots import Window

TZ = ZoneInfo("Europe/Tallinn")
VAT = 0.24
FORBIDDEN_TOMORROW_OR_WAIT = ["homme", "järgmis", "oota", "Homme", "Oota"]


def window(hour: int, minute: int, mean_eur_mwh: str) -> Window:
    start = datetime(2026, 10, 11, hour, minute, tzinfo=TZ)
    end = datetime.fromtimestamp(start.timestamp() + 3 * 3600, TZ)
    return Window(start=start, end=end, mean_eur_mwh=Decimal(mean_eur_mwh))


def remaining_series(price: float = 50.0) -> list[Interval]:
    start = datetime(2026, 10, 11, 8, 0, tzinfo=TZ).timestamp()
    return [
        Interval(start=datetime.fromtimestamp(start + 900 * i, TZ), price_eur_mwh=price)
        for i in range(64)  # 08:00 .. 23:45
    ]


def test_slot_line_matches_spec_example():
    # Spec: window 11:15-14:15 with display mean 4.21 senti/kWh -> "4.2 s/kWh".
    w = window(11, 15, "33.95")  # 33.95 * 1.24 / 10 = 4.2098
    text = format_daily_message(remaining_series(), [w], VAT)

    assert format_window_range(w) == "11:15–14:15"
    assert "11:15–14:15 · 4.2 s/kWh" in text


def test_three_slots_are_listed_cheapest_first_and_numbered():
    windows = [window(11, 15, "33.95"), window(15, 0, "40.00"), window(19, 30, "50.00")]
    text = format_daily_message(remaining_series(), windows, VAT)
    lines = text.splitlines()

    numbered = [line for line in lines if line[:2] in ("1.", "2.", "3.")]
    assert len(numbered) == 3
    assert numbered[0].startswith("1. 11:15–14:15")
    assert numbered[1].startswith("2. 15:00–18:00")
    assert numbered[2].startswith("3. 19:30–22:30")


def test_day_average_line_is_included():
    text = format_daily_message(remaining_series(50.0), [window(11, 15, "33.95")], VAT)
    # 50 EUR/MWh * 1.24 / 10 = 6.2 senti/kWh
    assert "Päeva keskmine: 6.2 s/kWh" in text


def test_day_average_is_mean_of_remaining_series_not_of_windows():
    series = remaining_series(10.0)
    series[0] = Interval(start=series[0].start, price_eur_mwh=10.0 + 12 * 4)  # one spike
    text = format_daily_message(series, [window(11, 15, "33.95")], VAT)
    # mean = (10*63 + 58)/64 = 10.75 -> *1.24/10 = 1.333 -> 1.3 (window mean would give 4.2)
    assert "Päeva keskmine: 1.3 s/kWh" in text


def test_short_remaining_day_says_too_short_and_lists_no_slots():
    text = format_daily_message(remaining_series(), [], VAT)

    assert "liiga vähe aega" in text
    assert "1. " not in text and "2. " not in text
    assert "Päeva keskmine" in text


def test_header_states_coverage_from_0800():
    text = format_daily_message(remaining_series(), [window(11, 15, "33.95")], VAT)
    assert "alates 08:00" in text.splitlines()[0]


def test_vat_footer_reports_configured_rate_and_no_network_fee():
    text = format_daily_message(remaining_series(), [window(11, 15, "33.95")], 0.20)
    assert "käibemaksu 20%" in text
    assert "võrgutasu ja aktsiisi ei ole arvestatud" in text


@pytest.mark.parametrize(
    "windows",
    [[], [window(11, 15, "33.95")], [window(11, 15, "33.95"), window(15, 0, "40.00"), window(19, 30, "50.00")]],
)
def test_never_mentions_tomorrow_or_advises_waiting(windows):
    text = format_daily_message(remaining_series(), windows, VAT)
    for word in FORBIDDEN_TOMORROW_OR_WAIT:
        assert word not in text, f"{word!r} found in message"


def test_empty_remaining_series_is_rejected():
    with pytest.raises(ValueError):
        format_daily_message([], [], VAT)
