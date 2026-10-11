from datetime import time
from zoneinfo import ZoneInfo

import pytest

from elektrihind.config import ConfigError, load_config

REQUIRED = {"TELEGRAM_BOT_TOKEN": "123:abc", "TELEGRAM_CHAT_ID": "-1001"}


def test_defaults_when_only_required_secrets_set():
    cfg = load_config(dict(REQUIRED))

    assert cfg.telegram_bot_token == "123:abc"
    assert cfg.telegram_chat_id == "-1001"
    assert cfg.vat == 0.24
    assert cfg.timezone == ZoneInfo("Europe/Tallinn")
    assert cfg.earliest_start is None
    assert cfg.latest_end is None


def test_explicit_values_override_defaults():
    env = {
        **REQUIRED,
        "VAT": "0.20",
        "TIMEZONE": "UTC",
        "EARLIEST_START": "09:30",
        "LATEST_END": "22:00",
    }
    cfg = load_config(env)

    assert cfg.vat == 0.20
    assert cfg.timezone == ZoneInfo("UTC")
    assert cfg.earliest_start == time(9, 30)
    assert cfg.latest_end == time(22, 0)


def test_empty_optional_values_fall_back_to_defaults():
    env = {**REQUIRED, "VAT": "", "TIMEZONE": "  ", "EARLIEST_START": "", "LATEST_END": ""}
    cfg = load_config(env)

    assert cfg.vat == 0.24
    assert cfg.timezone == ZoneInfo("Europe/Tallinn")
    assert cfg.earliest_start is None
    assert cfg.latest_end is None


@pytest.mark.parametrize("missing", ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"])
def test_missing_required_secret_raises(missing):
    env = {k: v for k, v in REQUIRED.items() if k != missing}

    with pytest.raises(ConfigError, match=missing):
        load_config(env)


def test_blank_required_secret_counts_as_missing():
    env = {**REQUIRED, "TELEGRAM_BOT_TOKEN": "   "}

    with pytest.raises(ConfigError, match="TELEGRAM_BOT_TOKEN"):
        load_config(env)


def test_both_secrets_missing_names_both():
    with pytest.raises(ConfigError) as exc:
        load_config({})

    assert "TELEGRAM_BOT_TOKEN" in str(exc.value)
    assert "TELEGRAM_CHAT_ID" in str(exc.value)


def test_malformed_vat_raises():
    with pytest.raises(ConfigError, match="VAT"):
        load_config({**REQUIRED, "VAT": "twenty-four"})


def test_unknown_timezone_raises():
    with pytest.raises(ConfigError, match="TIMEZONE"):
        load_config({**REQUIRED, "TIMEZONE": "Mars/Olympus"})


@pytest.mark.parametrize("name", ["EARLIEST_START", "LATEST_END"])
def test_malformed_time_bound_raises(name):
    with pytest.raises(ConfigError, match=name):
        load_config({**REQUIRED, name: "8am"})
