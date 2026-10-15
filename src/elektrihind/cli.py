"""Command-line entry points for the morning and afternoon price notifications."""

from __future__ import annotations

import argparse
import os
import sys
import time as time_module
from collections.abc import Mapping
from datetime import datetime, time, timedelta
from typing import Callable, TextIO

from elektrihind.config import ConfigError, load_config
from elektrihind.fetch import (
    HttpGet,
    PricesUnavailable,
    fetch_date_range_prices,
    fetch_day_prices,
    validate_complete_day,
)
from elektrihind.format import format_afternoon_message, format_daily_message
from elektrihind.notify import HttpPost, TelegramError, send_message
from elektrihind.slots import (
    afternoon_candidate_windows,
    afternoon_cutoff,
    candidate_windows,
    remaining_day_cutoff,
    select_three,
)

EXIT_OK = 0
EXIT_FAILURE = 1
POLL_INTERVAL = timedelta(minutes=5)
AFTERNOON_DEADLINE = time(18, 0)
Clock = Callable[[], datetime]
Sleep = Callable[[float], None]


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


def run_afternoon(
    env: Mapping[str, str],
    *,
    clock: Clock | None = None,
    sleep: Sleep | None = None,
    http_get: HttpGet | None = None,
    http_post: HttpPost | None = None,
    out: TextIO | None = None,
    err: TextIO | None = None,
) -> int:
    """Poll until tomorrow's full price series is published, then send once."""
    out = out or sys.stdout
    err = err or sys.stderr

    try:
        cfg = load_config(env)
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=err)
        return EXIT_FAILURE

    get_now = clock or (lambda: datetime.now(cfg.timezone))
    wait = sleep or time_module.sleep

    def local_now() -> datetime:
        return get_now().astimezone(cfg.timezone)

    started_at = local_now()
    today = started_at.date()
    tomorrow = today + timedelta(days=1)
    deadline = datetime.combine(today, AFTERNOON_DEADLINE, tzinfo=cfg.timezone)

    if started_at.timestamp() > deadline.timestamp():
        print(
            f"Prices unavailable for {tomorrow.isoformat()} by the 18:00 deadline. Nothing sent.",
            file=err,
        )
        return EXIT_FAILURE

    while True:
        attempt_at = local_now()
        if attempt_at.timestamp() > deadline.timestamp():
            print(
                f"Prices unavailable for {tomorrow.isoformat()} by the 18:00 deadline. Nothing sent.",
                file=err,
            )
            return EXIT_FAILURE
        try:
            intervals = fetch_date_range_prices(
                today, tomorrow, cfg.timezone, http_get=http_get
            )
            validate_complete_day(intervals, tomorrow, cfg.timezone)
        except PricesUnavailable as exc:
            failed_at = local_now()
            if failed_at.timestamp() >= deadline.timestamp():
                print(
                    f"Prices unavailable for {tomorrow.isoformat()} through 18:00: {exc}. Nothing sent.",
                    file=err,
                )
                return EXIT_FAILURE
            delay = min(
                POLL_INTERVAL.total_seconds(),
                deadline.timestamp() - failed_at.timestamp(),
            )
            wait(delay)
            continue

        available_at = local_now()
        if available_at.timestamp() > deadline.timestamp():
            print(
                f"Prices unavailable for {tomorrow.isoformat()} by the 18:00 deadline. Nothing sent.",
                file=err,
            )
            return EXIT_FAILURE

        cutoff = afternoon_cutoff(available_at, today)
        end_bound = datetime.combine(tomorrow + timedelta(days=1), time.min, tzinfo=cfg.timezone)
        cutoff_ts = cutoff.timestamp()
        end_bound_ts = end_bound.timestamp()
        eligible = [
            iv
            for iv in intervals
            if cutoff_ts <= iv.start.timestamp() < end_bound_ts
        ]
        if not eligible:
            print(
                f"No price intervals remain after {cutoff.strftime('%H:%M')} on {today.isoformat()}. Nothing sent.",
                file=err,
            )
            return EXIT_FAILURE

        windows = select_three(
            afternoon_candidate_windows(intervals, cutoff, end_bound)
        )
        text = format_afternoon_message(eligible, windows, cfg.vat, today)
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

        print(
            f"Sent {len(windows)} afternoon slot(s) for {today.isoformat()} from {cutoff.strftime('%H:%M')}.",
            file=out,
        )
        return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="elektrihind",
        description="Send today's remaining or afternoon cheapest 3-hour Nord Pool EE slots to Telegram.",
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=("afternoon",),
        help="run the afternoon flow using tomorrow's prices",
    )
    args = parser.parse_args(argv)
    if args.command == "afternoon":
        return run_afternoon(os.environ)
    return run(os.environ)
