"""Telegram Bot API sendMessage to a configured channel."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any

from elektrihind.config import ConfigError

TELEGRAM_API = "https://api.telegram.org"
DEFAULT_TIMEOUT = 15.0

# (url, json_body, headers) -> response body bytes. Raises on transport failure.
HttpPost = Callable[[str, bytes, dict[str, str]], bytes]


class TelegramError(Exception):
    """Telegram rejected the message or the request did not complete."""


def _default_http_post(url: str, body: bytes, headers: dict[str, str]) -> bytes:
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT) as resp:
            return resp.read()
    except urllib.error.HTTPError as exc:
        # Telegram returns a JSON error body with a 4xx status; hand it back for parsing.
        return exc.read()


def send_message(
    text: str,
    *,
    bot_token: str | None,
    chat_id: str | None,
    http_post: HttpPost | None = None,
) -> None:
    """Post `text` to `chat_id` via the Telegram Bot API.

    Raises ConfigError without making any request if the token or chat id is unset.
    Raises TelegramError if the request fails or Telegram responds with ok=false.
    The bot token is never included in raised error messages.
    """
    token = (bot_token or "").strip()
    chat = (chat_id or "").strip()
    missing = [name for name, value in (("TELEGRAM_BOT_TOKEN", token), ("TELEGRAM_CHAT_ID", chat)) if not value]
    if missing:
        raise ConfigError("cannot send Telegram message, missing: " + ", ".join(missing))

    url = f"{TELEGRAM_API}/bot{token}/sendMessage"
    body = json.dumps({"chat_id": chat, "text": text}, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json; charset=utf-8"}
    post = http_post or _default_http_post

    try:
        raw = post(url, body, headers)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        # Do not chain `exc` with its URL-bearing message; keep only the exception type.
        raise TelegramError(f"Telegram request failed ({type(exc).__name__})") from None

    _check_response(raw)


def _check_response(raw: bytes) -> None:
    try:
        payload: Any = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TelegramError("Telegram returned a non-JSON response") from exc

    if not isinstance(payload, dict) or payload.get("ok") is not True:
        description = payload.get("description") if isinstance(payload, dict) else None
        detail = f": {description}" if description else ""
        raise TelegramError(f"Telegram rejected the message{detail}")
