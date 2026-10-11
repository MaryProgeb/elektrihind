import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

import pytest

from elektrihind.cli import run

TZ = ZoneInfo("Europe/Tallinn")
FIXTURES = Path(__file__).parent / "fixtures"
ENV = {"TELEGRAM_BOT_TOKEN": "123:TOKEN", "TELEGRAM_CHAT_ID": "-100555"}
RUN_AT_0807 = datetime(2026, 10, 11, 8, 7, tzinfo=TZ)


class FakeGet:
    def __init__(self, body: bytes):
        self.body = body
        self.urls: list[str] = []

    def __call__(self, url: str) -> bytes:
        self.urls.append(url)
        return self.body


class FakePost:
    def __init__(self, response: bytes = b'{"ok": true, "result": {}}'):
        self.response = response
        self.calls: list[tuple[str, dict]] = []

    def __call__(self, url, body, headers):
        self.calls.append((url, json.loads(body)))
        return self.response


def fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def slot_starts(text: str) -> list[str]:
    return re.findall(r"^\d\. (\d{2}:\d{2})–", text, flags=re.MULTILINE)


def test_happy_path_sends_one_message_with_remaining_today_slots(capsys):
    get = FakeGet(fixture("elering_ee_24h.json"))
    post = FakePost()

    code = run(ENV, RUN_AT_0807, http_get=get, http_post=post)

    assert code == 0
    assert len(post.calls) == 1
    url, payload = post.calls[0]
    assert url == "https://api.telegram.org/bot123:TOKEN/sendMessage"
    assert payload["chat_id"] == "-100555"

    text = payload["text"]
    assert text.splitlines()[0] == "Elektrihind täna alates 08:00"
    assert "Päeva keskmine" in text
    assert "homme" not in text.lower()

    starts = slot_starts(text)
    assert 1 <= len(starts) <= 3
    # Listed cheapest-first (rank order, not clock order).
    prices = [float(p) for p in re.findall(r"^\d\. \S+ · (-?[\d.]+) s/kWh", text, flags=re.MULTILINE)]
    assert len(prices) == len(starts)
    assert prices == sorted(prices)
    assert "Sent" in capsys.readouterr().out


def test_cutoff_excludes_intervals_that_started_before_run_time():
    # Run at 08:07: the 08:00 and 08:00-08:15 products have started; cutoff is 08:15.
    post = FakePost()
    run(ENV, RUN_AT_0807, http_get=FakeGet(fixture("elering_ee_24h.json")), http_post=post)

    text = post.calls[0][1]["text"]
    assert all(start >= "08:15" for start in slot_starts(text))


def test_only_today_is_requested_never_tomorrow():
    get = FakeGet(fixture("elering_ee_24h.json"))

    run(ENV, RUN_AT_0807, http_get=get, http_post=FakePost())

    assert len(get.urls) == 1
    query = parse_qs(urlparse(get.urls[0]).query)
    # Window is 2026-10-11 00:00 EEST -> 2026-10-12 00:00 EEST, i.e. one local day only.
    assert query["start"] == ["2026-10-10T21:00:00Z"]
    assert query["end"] == ["2026-10-11T21:00:00Z"]


def test_missing_secret_exits_nonzero_and_does_not_fetch_or_send(capsys):
    get = FakeGet(fixture("elering_ee_24h.json"))
    post = FakePost()

    code = run({"TELEGRAM_CHAT_ID": "-100555"}, RUN_AT_0807, http_get=get, http_post=post)

    assert code == 1
    assert get.urls == []
    assert post.calls == []
    assert "TELEGRAM_BOT_TOKEN" in capsys.readouterr().err


def test_unavailable_prices_send_nothing_and_exit_nonzero(capsys):
    post = FakePost()

    code = run(ENV, RUN_AT_0807, http_get=FakeGet(fixture("elering_ee_empty.json")), http_post=post)

    assert code == 1
    assert post.calls == []
    assert "Prices unavailable" in capsys.readouterr().err


def test_transport_failure_sends_nothing(capsys):
    import urllib.error

    def broken(url: str) -> bytes:
        raise urllib.error.URLError("dns failure")

    post = FakePost()
    code = run(ENV, RUN_AT_0807, http_get=broken, http_post=post)

    assert code == 1
    assert post.calls == []


def test_telegram_rejection_exits_nonzero(capsys):
    post = FakePost(response=b'{"ok": false, "description": "chat not found"}')

    code = run(ENV, RUN_AT_0807, http_get=FakeGet(fixture("elering_ee_24h.json")), http_post=post)

    assert code == 1
    assert "chat not found" in capsys.readouterr().err


def test_late_day_run_still_sends_short_day_message():
    # 23:00 run: only four products (23:00-23:45) remain, so no 3-hour slot fits.
    post = FakePost()
    now = datetime(2026, 10, 11, 23, 0, tzinfo=TZ)

    code = run(ENV, now, http_get=FakeGet(fixture("elering_ee_24h.json")), http_post=post)

    assert code == 0
    text = post.calls[0][1]["text"]
    assert "liiga vähe aega" in text
    assert slot_starts(text) == []


def test_no_intervals_after_cutoff_sends_nothing(capsys):
    # Run after the last product of the day has started: nothing remains.
    post = FakePost()
    now = datetime(2026, 10, 12, 0, 0, tzinfo=TZ)

    code = run(ENV, now, http_get=FakeGet(fixture("elering_ee_24h.json")), http_post=post)

    assert code == 1
    assert post.calls == []


def test_dst_day_runs_with_23_hour_series():
    post = FakePost()
    now = datetime(2026, 3, 29, 8, 7, tzinfo=TZ)

    code = run(ENV, now, http_get=FakeGet(fixture("elering_ee_dst_23h.json")), http_post=post)

    assert code == 0
    assert "Elektrihind täna alates 08:00" in post.calls[0][1]["text"]


@pytest.mark.parametrize("name", ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"])
def test_blank_secret_is_treated_as_missing(name, capsys):
    env = {**ENV, name: "  "}
    post = FakePost()

    code = run(env, RUN_AT_0807, http_get=FakeGet(fixture("elering_ee_24h.json")), http_post=post)

    assert code == 1
    assert post.calls == []
