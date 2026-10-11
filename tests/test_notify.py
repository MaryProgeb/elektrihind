import io
import json
import urllib.error
import urllib.request

import pytest

from elektrihind.config import ConfigError
from elektrihind.notify import TelegramError, send_message

TOKEN = "123456:SECRET-TOKEN-VALUE"
CHAT = "-1001234567890"
TEXT = "Elektrihind täna alates 08:00"


class FakePost:
    def __init__(self, response: bytes = b'{"ok": true, "result": {"message_id": 1}}', exc=None):
        self.response = response
        self.exc = exc
        self.calls: list[tuple[str, bytes, dict[str, str]]] = []

    def __call__(self, url: str, body: bytes, headers: dict[str, str]) -> bytes:
        self.calls.append((url, body, headers))
        if self.exc is not None:
            raise self.exc
        return self.response


def test_sends_text_to_configured_chat_via_send_message_endpoint():
    post = FakePost()

    send_message(TEXT, bot_token=TOKEN, chat_id=CHAT, http_post=post)

    assert len(post.calls) == 1
    url, body, headers = post.calls[0]
    assert url == f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    assert json.loads(body) == {"chat_id": CHAT, "text": TEXT}
    assert headers["Content-Type"].startswith("application/json")


def test_text_is_sent_as_utf8_estonian():
    post = FakePost()

    send_message(TEXT, bot_token=TOKEN, chat_id=CHAT, http_post=post)

    _, body, _ = post.calls[0]
    assert "täna".encode("utf-8") in body


def test_missing_token_raises_config_error_and_does_not_send():
    post = FakePost()

    with pytest.raises(ConfigError, match="TELEGRAM_BOT_TOKEN"):
        send_message(TEXT, bot_token=None, chat_id=CHAT, http_post=post)

    assert post.calls == []


def test_blank_token_counts_as_missing():
    post = FakePost()

    with pytest.raises(ConfigError, match="TELEGRAM_BOT_TOKEN"):
        send_message(TEXT, bot_token="   ", chat_id=CHAT, http_post=post)

    assert post.calls == []


def test_missing_chat_id_raises_config_error_and_does_not_send():
    post = FakePost()

    with pytest.raises(ConfigError, match="TELEGRAM_CHAT_ID"):
        send_message(TEXT, bot_token=TOKEN, chat_id="", http_post=post)

    assert post.calls == []


def test_ok_false_response_raises_with_telegram_description():
    post = FakePost(response=b'{"ok": false, "error_code": 400, "description": "chat not found"}')

    with pytest.raises(TelegramError, match="chat not found"):
        send_message(TEXT, bot_token=TOKEN, chat_id=CHAT, http_post=post)


def test_non_json_response_raises_telegram_error():
    post = FakePost(response=b"<html>bad gateway</html>")

    with pytest.raises(TelegramError, match="non-JSON"):
        send_message(TEXT, bot_token=TOKEN, chat_id=CHAT, http_post=post)


def test_transport_failure_raises_telegram_error_without_leaking_token():
    post = FakePost(exc=urllib.error.URLError(f"no route to api.telegram.org/bot{TOKEN}"))

    with pytest.raises(TelegramError) as exc_info:
        send_message(TEXT, bot_token=TOKEN, chat_id=CHAT, http_post=post)

    assert TOKEN not in str(exc_info.value)
    assert exc_info.value.__cause__ is None


def test_timeout_raises_telegram_error():
    post = FakePost(exc=TimeoutError("timed out"))

    with pytest.raises(TelegramError, match="TimeoutError"):
        send_message(TEXT, bot_token=TOKEN, chat_id=CHAT, http_post=post)


def test_default_transport_returns_error_body_on_http_401(monkeypatch):
    body = json.dumps({"ok": False, "error_code": 401, "description": "Unauthorized"}).encode()

    def fake_urlopen(req, timeout=None):
        assert isinstance(req, urllib.request.Request)
        raise urllib.error.HTTPError(req.full_url, 401, "Unauthorized", {}, io.BytesIO(body))

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    with pytest.raises(TelegramError, match="Unauthorized"):
        send_message(TEXT, bot_token=TOKEN, chat_id=CHAT)


def test_default_transport_success_path(monkeypatch):
    class Resp(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def fake_urlopen(req, timeout=None):
        assert req.get_method() == "POST"
        return Resp(b'{"ok": true, "result": {}}')

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    send_message(TEXT, bot_token=TOKEN, chat_id=CHAT)
