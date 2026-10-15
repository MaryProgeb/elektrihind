import json
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from elektrihind import cli
from elektrihind.cli import run_afternoon

TZ = ZoneInfo("Europe/Tallinn")
FIXTURES = Path(__file__).parent / "fixtures"
ENV = {"TELEGRAM_BOT_TOKEN": "123:TOKEN", "TELEGRAM_CHAT_ID": "-100555"}
TODAY = date(2026, 10, 11)


def rows_for_day(day: date) -> list[dict[str, int | float]]:
    start = datetime.combine(day, time.min, tzinfo=TZ).timestamp()
    end = datetime.combine(day + timedelta(days=1), time.min, tzinfo=TZ).timestamp()
    return [
        {"timestamp": int(ts), "price": 50.0}
        for ts in range(int(start), int(end), 900)
    ]


def price_payload(*, complete_tomorrow: bool = True) -> bytes:
    rows = rows_for_day(TODAY) + rows_for_day(TODAY + timedelta(days=1))
    if not complete_tomorrow:
        rows.pop()
    return json.dumps({"success": True, "data": {"ee": rows}}).encode()


class FakeGet:
    def __init__(self, bodies: list[bytes]):
        self.bodies = bodies
        self.urls: list[str] = []

    def __call__(self, url: str) -> bytes:
        self.urls.append(url)
        return self.bodies[min(len(self.urls) - 1, len(self.bodies) - 1)]


class FakePost:
    def __init__(self):
        self.calls: list[tuple[str, dict]] = []

    def __call__(self, url, body, headers):
        self.calls.append((url, json.loads(body)))
        return b'{"ok": true, "result": {}}'


class FakeClock:
    def __init__(self, now: datetime):
        self.now = now
        self.sleeps: list[float] = []

    def __call__(self) -> datetime:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now = datetime.fromtimestamp(self.now.timestamp() + seconds, TZ)


def test_first_complete_poll_sends_and_1507_cutoff_starts_at_1515(capsys):
    clock = FakeClock(datetime(2026, 10, 11, 15, 7, tzinfo=TZ))
    get = FakeGet([price_payload()])
    post = FakePost()

    code = run_afternoon(ENV, clock=clock, sleep=clock.sleep, http_get=get, http_post=post)

    assert code == 0
    assert len(get.urls) == 1
    assert len(post.calls) == 1
    text = post.calls[0][1]["text"]
    assert text.startswith("Elektrihind täna 15:00 kuni ülehomme 00:00")
    assert "täna 15:15–18:15" in text
    assert clock.sleeps == []
    assert "Sent" in capsys.readouterr().out


def test_later_publication_retries_then_sends_complete_series():
    clock = FakeClock(datetime(2026, 10, 11, 15, 7, tzinfo=TZ))
    get = FakeGet(
        [
            price_payload(complete_tomorrow=False),
            price_payload(complete_tomorrow=False),
            price_payload(),
        ]
    )
    post = FakePost()

    code = run_afternoon(ENV, clock=clock, sleep=clock.sleep, http_get=get, http_post=post)

    assert code == 0
    assert len(get.urls) == 3
    assert clock.sleeps == [300, 300]
    assert len(post.calls) == 1
    text = post.calls[0][1]["text"]
    assert "täna 15:30–18:30" in text
    assert "Perioodi keskmine" in text


def test_deadline_gets_final_fetch_at_1800_and_never_sends(capsys):
    clock = FakeClock(datetime(2026, 10, 11, 17, 57, tzinfo=TZ))
    get = FakeGet([price_payload(complete_tomorrow=False)])
    post = FakePost()

    code = run_afternoon(ENV, clock=clock, sleep=clock.sleep, http_get=get, http_post=post)

    assert code == 1
    assert len(get.urls) == 2
    assert clock.sleeps == [180]
    assert clock.now == datetime(2026, 10, 11, 18, 0, tzinfo=TZ)
    assert post.calls == []
    assert "18:00" in capsys.readouterr().err


def test_run_after_deadline_does_not_fetch_or_send(capsys):
    clock = FakeClock(datetime(2026, 10, 11, 18, 1, tzinfo=TZ))
    get = FakeGet([price_payload()])
    post = FakePost()

    code = run_afternoon(ENV, clock=clock, sleep=clock.sleep, http_get=get, http_post=post)

    assert code == 1
    assert get.urls == []
    assert post.calls == []
    assert "18:00" in capsys.readouterr().err


def test_afternoon_main_routes_command_and_default_to_separate_flows(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(cli, "run", lambda env: calls.append("morning") or 0)
    monkeypatch.setattr(cli, "run_afternoon", lambda env: calls.append("afternoon") or 0)

    assert cli.main([]) == 0
    assert cli.main(["afternoon"]) == 0
    assert calls == ["morning", "afternoon"]


def test_afternoon_module_uses_complete_fixture_tomorrow():
    body = (FIXTURES / "elering_ee_24h.json").read_bytes()
    # The established fixture is a complete 2026-10-11 series (tomorrow for this run).
    clock = FakeClock(datetime(2026, 10, 10, 15, 7, tzinfo=TZ))
    get = FakeGet([body])
    post = FakePost()

    code = run_afternoon(ENV, clock=clock, sleep=clock.sleep, http_get=get, http_post=post)

    assert code == 0
    assert len(post.calls) == 1
    assert "homme" in post.calls[0][1]["text"]
