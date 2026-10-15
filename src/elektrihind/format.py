"""VAT conversion and Estonian message formatting."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from elektrihind.fetch import Interval
from elektrihind.slots import Window

TENTH = Decimal("0.1")
TEN = Decimal(10)


def eur_mwh_to_senti_kwh(eur_mwh: float | Decimal, vat: float) -> Decimal:
    """Convert source EUR/MWh (excl. VAT) to senti/kWh including VAT.

    Formula: (EUR/MWh) * (1 + VAT) / 10. No network fee or excise is added.
    Uses Decimal to avoid binary float drift (100 EUR/MWh -> exactly 12.4).
    """
    price = Decimal(str(eur_mwh))
    rate = Decimal(1) + Decimal(str(vat))
    return price * rate / TEN


def round_senti(value: Decimal) -> Decimal:
    """Round to one decimal place, ties away from zero."""
    return value.quantize(TENTH, rounding=ROUND_HALF_UP)


def _senti_text(eur_mwh: float | Decimal, vat: float) -> str:
    return str(round_senti(eur_mwh_to_senti_kwh(eur_mwh, vat)))


def _hhmm(moment) -> str:
    return moment.strftime("%H:%M")


def format_window_range(window: Window) -> str:
    """Local start-end, e.g. 11:15–14:15."""
    return f"{_hhmm(window.start)}–{_hhmm(window.end)}"


def day_average_eur_mwh(remaining: Sequence[Interval]) -> Decimal:
    """Arithmetic mean of source prices across the remaining-today series."""
    total = sum((Decimal(str(iv.price_eur_mwh)) for iv in remaining), Decimal(0))
    return total / len(remaining)


def format_daily_message(
    remaining: Sequence[Interval],
    windows: Sequence[Window],
    vat: float,
) -> str:
    """Estonian Telegram text for the 08:00 remaining-today message.

    `remaining` is the eligible remaining-day series (after the cutoff); its mean is
    shown as `Päeva keskmine`. `windows` are the selected cheapest-first slots, possibly
    empty. The text never mentions tomorrow or advises waiting.
    """
    if not remaining:
        raise ValueError("format_daily_message needs a non-empty remaining-day series")

    vat_pct = f"{round(vat * 100, 2):g}%"
    lines = ["Elektrihind täna alates 08:00"]

    if windows:
        lines.append("Odavaimad 3-tunnised ajavahemikud:")
        for number, window in enumerate(windows, start=1):
            price = _senti_text(window.mean_eur_mwh, vat)
            lines.append(f"{number}. {format_window_range(window)} · {price} s/kWh")
    else:
        lines.append("Täna alates 08:00 on jäänud liiga vähe aega 3-tunniseks ajavahemikuks.")

    lines.append("")
    lines.append(f"Päeva keskmine: {_senti_text(day_average_eur_mwh(remaining), vat)} s/kWh")
    lines.append(f"Hinnad sisaldavad käibemaksu {vat_pct}; võrgutasu ja aktsiisi ei ole arvestatud.")
    return "\n".join(lines)


def _estonian_date_label(moment, today: date) -> str:
    offset = (moment.date() - today).days
    if offset <= 0:
        return "täna"
    if offset == 1:
        return "homme"
    if offset == 2:
        return "ülehomme"
    return moment.strftime("%d.%m")


def format_afternoon_window_range(window: Window, today: date) -> str:
    """Date-qualified local endpoints for a multi-day afternoon window."""
    start_label = _estonian_date_label(window.start, today)
    end_label = _estonian_date_label(window.end, today)
    if window.start.date() == window.end.date():
        return f"{start_label} {_hhmm(window.start)}–{_hhmm(window.end)}"
    return f"{start_label} {_hhmm(window.start)}–{end_label} {_hhmm(window.end)}"


def format_afternoon_message(
    eligible: Sequence[Interval],
    windows: Sequence[Window],
    vat: float,
    today: date,
) -> str:
    """Estonian message for eligible prices from 15:00 today through tomorrow."""
    if not eligible:
        raise ValueError("format_afternoon_message needs a non-empty eligible series")

    total = sum((Decimal(str(iv.price_eur_mwh)) for iv in eligible), Decimal(0))
    period_average = total / len(eligible)
    vat_pct = f"{round(vat * 100, 2):g}%"
    lines = ["Elektrihind täna 15:00 kuni ülehomme 00:00"]

    if windows:
        lines.append("Odavaimad 3-tunnised ajavahemikud:")
        for number, window in enumerate(windows, start=1):
            price = _senti_text(window.mean_eur_mwh, vat)
            period = format_afternoon_window_range(window, today)
            lines.append(f"{number}. {period} · {price} s/kWh")
    else:
        lines.append("Sellel perioodil ei mahu ühtegi 3-tunnist ajavahemikku.")

    lines.append("")
    lines.append(f"Perioodi keskmine: {_senti_text(period_average, vat)} s/kWh")
    lines.append(f"Hinnad sisaldavad käibemaksu {vat_pct}; võrgutasu ja aktsiisi ei ole arvestatud.")
    return "\n".join(lines)
