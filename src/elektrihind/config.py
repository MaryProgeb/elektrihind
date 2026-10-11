"""Environment-based configuration."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DEFAULT_VAT = 0.24
DEFAULT_TIMEZONE = "Europe/Tallinn"


class ConfigError(Exception):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True)
class Config:
    telegram_bot_token: str
    telegram_chat_id: str
    vat: float
    timezone: ZoneInfo
    earliest_start: time | None
    latest_end: time | None


def _get(env: Mapping[str, str], name: str) -> str | None:
    value = env.get(name)
    if value is None:
        return None
    value = value.strip()
    return value or None


def _parse_hhmm(name: str, raw: str) -> time:
    try:
        return datetime.strptime(raw, "%H:%M").time()
    except ValueError as exc:
        raise ConfigError(f"{name} must be HH:MM local time, got {raw!r}") from exc


def load_config(env: Mapping[str, str]) -> Config:
    """Build Config from an environment mapping.

    Raises ConfigError if TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is unset or empty,
    or if an optional value is malformed.
    """
    bot_token = _get(env, "TELEGRAM_BOT_TOKEN")
    chat_id = _get(env, "TELEGRAM_CHAT_ID")
    missing = [
        name
        for name, value in (("TELEGRAM_BOT_TOKEN", bot_token), ("TELEGRAM_CHAT_ID", chat_id))
        if value is None
    ]
    if missing:
        raise ConfigError("missing required environment variables: " + ", ".join(missing))

    raw_vat = _get(env, "VAT")
    if raw_vat is None:
        vat = DEFAULT_VAT
    else:
        try:
            vat = float(raw_vat)
        except ValueError as exc:
            raise ConfigError(f"VAT must be a decimal fraction such as 0.24, got {raw_vat!r}") from exc

    tz_name = _get(env, "TIMEZONE") or DEFAULT_TIMEZONE
    try:
        timezone = ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ConfigError(f"TIMEZONE is not a known IANA zone: {tz_name!r}") from exc

    raw_start = _get(env, "EARLIEST_START")
    raw_end = _get(env, "LATEST_END")
    earliest_start = _parse_hhmm("EARLIEST_START", raw_start) if raw_start else None
    latest_end = _parse_hhmm("LATEST_END", raw_end) if raw_end else None

    return Config(
        telegram_bot_token=bot_token,
        telegram_chat_id=chat_id,
        vat=vat,
        timezone=timezone,
        earliest_start=earliest_start,
        latest_end=latest_end,
    )
