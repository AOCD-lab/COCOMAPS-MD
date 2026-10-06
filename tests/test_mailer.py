"""Tests for the job-completed email notification."""
import smtplib

import pytest

from backend import mailer
from backend.routes import upload


SMTP_ENV = {
    "SMTP_HOST": "smtp.example.org",
    "SMTP_PORT": "587",
    "SMTP_USER": "user",
    "SMTP_PASSWORD": "secret",
    "SMTP_FROM": "COCOMAPS-MD <no-reply@example.org>",
    "COCOMAPS_PUBLIC_URL": "https://example.org/BioTools/COCOMAPS-MD/",
}


@pytest.fixture()
def smtp_env(monkeypatch):
    for key in ("SMTP_SECURITY", "SMTP_TIMEOUT"):
        monkeypatch.delenv(key, raising=False)
    for key, value in SMTP_ENV.items():
        monkeypatch.setenv(key, value)


class FakeSMTP:
    instances = []

    def __init__(self, host, port, timeout=None, context=None):
        self.host, self.port = host, port
        self.started_tls = False
        self.logged_in = None
        self.sent = []
        FakeSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self, context=None):
        self.started_tls = True

    def login(self, user, password):
        self.logged_in = (user, password)

    def send_message(self, msg):
        self.sent.append(msg)


@pytest.fixture()
def fake_smtp(monkeypatch):
    FakeSMTP.instances = []
    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    monkeypatch.setattr(smtplib, "SMTP_SSL", FakeSMTP)
    return FakeSMTP


@pytest.mark.parametrize("address", ["a@b.it", "first.last+tag@example.org"])
def test_valid_emails(address):
    assert mailer.is_valid_email(address)


@pytest.mark.parametrize(
    "address",
    ["", "no-at-sign", "a@b", "a b@c.it", "a@b.it\nBcc: x@y.it", "a@b.it, c@d.it", None, 42],
)
def test_invalid_emails(address):
    assert not mailer.is_valid_email(address)


def test_not_configured_without_env(monkeypatch):
    for key in SMTP_ENV:
        monkeypatch.delenv(key, raising=False)
    assert not mailer.is_configured()
    assert mailer.send_job_completed_email("a@b.it", "job", "2026001-ABCDEFGH") is False


def test_build_analysis_url_uses_public_url_and_quotes_id(smtp_env):
    assert (
        mailer.build_analysis_url("2026001-ABCDEFGH")
        == "https://example.org/BioTools/COCOMAPS-MD/analysis/2026001-ABCDEFGH"
    )
    assert mailer.build_analysis_url("a/b").endswith("/analysis/a%2Fb")


def test_sends_email_with_link_and_starttls(smtp_env, fake_smtp):
    ok = mailer.send_job_completed_email(
        "me@example.com", "My job", "2026001-ABCDEFGH", expires_at="2026-08-01T00:00:00Z"
    )
    assert ok is True
    server = fake_smtp.instances[0]
    assert (server.host, server.port) == ("smtp.example.org", 587)
    assert server.started_tls is True
    assert server.logged_in == ("user", "secret")
    msg = server.sent[0]
    assert msg["To"] == "me@example.com"
    assert msg["From"] == SMTP_ENV["SMTP_FROM"]
    body = msg.get_content()
    assert "https://example.org/BioTools/COCOMAPS-MD/analysis/2026001-ABCDEFGH" in body
    assert "2026-08-01T00:00:00Z" in body


def test_no_login_when_user_empty_and_ssl_mode(smtp_env, fake_smtp, monkeypatch):
    monkeypatch.setenv("SMTP_USER", "")
    monkeypatch.setenv("SMTP_SECURITY", "ssl")
    monkeypatch.setenv("SMTP_PORT", "465")
    assert mailer.send_job_completed_email("me@example.com", "j", "ID1") is True
    server = fake_smtp.instances[0]
    assert server.port == 465
    assert server.logged_in is None
    assert server.started_tls is False


def test_subject_is_sanitised(smtp_env, fake_smtp):
    mailer.send_job_completed_email("me@example.com", "evil\r\nBcc: x@y.it", "ID1")
    msg = fake_smtp.instances[0].sent[0]
    assert "\n" not in msg["Subject"] and "\r" not in msg["Subject"]
    assert msg["Bcc"] is None


def test_smtp_failure_is_swallowed(smtp_env, monkeypatch):
    def boom(*args, **kwargs):
        raise smtplib.SMTPConnectError(421, "down")

    monkeypatch.setattr(smtplib, "SMTP", boom)
    assert mailer.send_job_completed_email("me@example.com", "j", "ID1") is False


def test_invalid_recipient_not_sent(smtp_env, fake_smtp):
    assert mailer.send_job_completed_email("not-an-email", "j", "ID1") is False
    assert fake_smtp.instances == []


def test_notify_helper_skips_when_no_email(monkeypatch):
    calls = []
    monkeypatch.setattr(mailer, "send_job_completed_email", lambda *a: calls.append(a))
    upload._notify_job_completed("", "j", "ID1", None)
    assert calls == []


def test_notify_helper_sends_in_background(monkeypatch):
    import threading

    done = threading.Event()
    calls = []

    def fake_send(*args):
        calls.append(args)
        done.set()
        return True

    monkeypatch.setattr(mailer, "send_job_completed_email", fake_send)
    upload._notify_job_completed("me@example.com", "My job", "2026001-ABCDEFGH", "2026-08-01T00:00:00Z")
    assert done.wait(timeout=2)
    assert calls == [("me@example.com", "My job", "2026001-ABCDEFGH", "2026-08-01T00:00:00Z")]
