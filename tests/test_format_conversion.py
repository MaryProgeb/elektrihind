from decimal import Decimal

import pytest

from elektrihind.format import eur_mwh_to_senti_kwh, round_senti


def test_100_eur_mwh_with_default_vat_is_12_4_senti():
    value = eur_mwh_to_senti_kwh(100, 0.24)
    assert value == Decimal("12.4")
    assert round_senti(value) == Decimal("12.4")


def test_negative_price_stays_negative():
    value = eur_mwh_to_senti_kwh(-10, 0.24)
    assert value == Decimal("-1.24")
    assert round_senti(value) == Decimal("-1.2")


def test_zero_price():
    assert eur_mwh_to_senti_kwh(0, 0.24) == Decimal("0")


def test_custom_vat_rate():
    assert eur_mwh_to_senti_kwh(100, 0.20) == Decimal("12.0")


def test_no_network_fee_or_excise_is_added():
    # Only VAT is applied; 50 EUR/MWh -> 6.2 senti/kWh at 24%.
    assert eur_mwh_to_senti_kwh(50, 0.24) == Decimal("6.2")


@pytest.mark.parametrize(
    "value, expected",
    [
        (Decimal("4.25"), Decimal("4.3")),
        (Decimal("4.24"), Decimal("4.2")),
        (Decimal("-4.25"), Decimal("-4.3")),
        (Decimal("-4.24"), Decimal("-4.2")),
    ],
)
def test_rounding_ties_go_away_from_zero(value, expected):
    assert round_senti(value) == expected
