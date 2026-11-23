"""The digest is sent at most once per digest date (SBC_Tool-erv).

Two scheduled tasks used to call daily_digest_email.py (07:00 daily and 17:45
Mon-Fri), and nothing stopped a second send. send_digest now records the date
it sent for in the `digest_sent_for` setting and skips a repeat, unless the run
is forced or is a one-off to an override address (a test mail must neither be
blocked nor count as the day's digest).

    py -3 -m pytest tools/test_digest_idempotency.py -q
"""
from datetime import date

import pytest

import daily_digest_email as dde


class _FakeSMTP:
    sent: list = []

    def __init__(self, *a, **k):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def login(self, *a):
        pass

    def sendmail(self, frm, to, body):
        _FakeSMTP.sent.append(to)


@pytest.fixture
def env(monkeypatch):
    settings: dict[str, str] = {}
    _FakeSMTP.sent = []
    monkeypatch.setattr(dde.db, "get_setting", lambda k, d=None: settings.get(k, d))
    monkeypatch.setattr(dde.db, "set_setting", lambda k, v: settings.__setitem__(k, v))
    monkeypatch.setattr(dde, "get_credentials", lambda: ("me@x", "pw", "you@x"))
    monkeypatch.setattr(dde, "render_html", lambda d: "<p>digest</p>")
    monkeypatch.setattr(dde.smtplib, "SMTP_SSL", _FakeSMTP)
    return settings


D = date(2026, 11, 24)


def test_second_send_for_the_same_date_is_skipped(env, capsys):
    dde.send_digest(today=D)
    dde.send_digest(today=D)
    assert len(_FakeSMTP.sent) == 1
    assert env["digest_sent_for"] == "2026-11-24"
    assert "already sent" in capsys.readouterr().out


def test_a_new_date_sends_again(env):
    dde.send_digest(today=D)
    dde.send_digest(today=date(2026, 11, 25))
    assert len(_FakeSMTP.sent) == 2
    assert env["digest_sent_for"] == "2026-11-25"


def test_force_resends(env):
    dde.send_digest(today=D)
    dde.send_digest(today=D, force=True)
    assert len(_FakeSMTP.sent) == 2


def test_override_recipient_is_neither_blocked_nor_recorded(env):
    dde.send_digest(today=D)
    dde.send_digest(today=D, to_override="test@x")
    assert _FakeSMTP.sent == [["you@x"], ["test@x"]]
    dde.send_digest(to_override="test@x", today=date(2026, 11, 26))
    assert env["digest_sent_for"] == "2026-11-24"


def test_failed_send_is_not_recorded(env, monkeypatch):
    class Boom(_FakeSMTP):
        def sendmail(self, *a):
            raise OSError("smtp down")
    monkeypatch.setattr(dde.smtplib, "SMTP_SSL", Boom)
    with pytest.raises(OSError):
        dde.send_digest(today=D)
    assert "digest_sent_for" not in env
