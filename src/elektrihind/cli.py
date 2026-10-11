"""Entry point for `python -m elektrihind`: fetch -> slots -> notify for remaining today."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Mapping
from datetime import datetime
from typing import TextIO

from elektrihind.config import ConfigError, load_config
from elektrihind.fetch import HttpGet, PricesUnavailable, fetch_day_prices
from elektrihind.format import format_daily_message
from elektrihind.notify import HttpPost, TelegramError, send_message
from elektrihind.slots import candidate_windows, remaining_day_cutoff, select_three

EXIT_OK = 0
EXIT_FAILURE = 1


def run(
    env: Mapping[str, str],
    now: datetime | None = None,
    *,
    http_get: HttpGet | None = None,
    http_post: HttpPost | None = None,
    out: TextIO | None = None,
    err: TextIO | None = None,
) -> int:
    """Run the remaining-today flow once. Returns a process exit code.

    Fetches only today's Europe/Tallinn prices, selects up to three cheapest
    non-overlapping 3-hour windows from the cutoff onward, and posts one Estonian
    message. Nothing is sent if configuration is missing or prices are unavailable.
    """
    out = out or sys.stdout
    err = err or sys.stderr

    try:
        cfg = load_config(env)
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=err)
        return EXIT_FAILURE

    now_local = (now or datetime.now(cfg.timezone)).astimezone(cfg.timezone)
    today = now_local.date()

    try:
        intervals = fetch_day_prices(today, cfg.timezone, http_get=http_get)
    except PricesUnavailable as exc:
        print(f"Prices unavailable for {today.isoformat()}: {exc}. Nothing sent.", file=err)
        return EXIT_FAILURE

    cutoff = remaining_day_cutoff(now_local, today, earliest_start=cfg.earliest_start)
    remaining = [iv for iv in intervals if iv.start.timestamp() >= cutoff.timestamp()]
    if not remaining:
        print(
            f"No price intervals remain after {cutoff.strftime('%H:%M')} on {today.isoformat()}. Nothing sent.",
            file=err,
        )
        return EXIT_FAILURE

    windows = select_three(candidate_windows(intervals, cutoff, latest_end=cfg.latest_end))
    text = format_daily_message(remaining, windows, cfg.vat)

    try:
        send_message(
            text,
            bot_token=cfg.telegram_bot_token,
            chat_id=cfg.telegram_chat_id,
            http_post=http_post,
        )
    except (ConfigError, TelegramError) as exc:
        print(f"Telegram send failed: {exc}", file=err)
        return EXIT_FAILURE

    print(f"Sent {len(windows)} slot(s) for {today.isoformat()} from {cutoff.strftime('%H:%M')}.", file=out)
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="elektrihind",
        description="Send today's cheapest 3-hour Nord Pool EE slots (from 08:00) to a Telegram channel.",
    )
    parser.parse_args(argv)
    return run(os.environ)
