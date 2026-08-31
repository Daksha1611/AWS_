"""Credential loading, which had no tests and turned out to matter enormously.

Nothing in the gateway process called `load()`, so `.env` was never read, and
every component that decides whether the system is real - the Razorpay rail, the
Firestore ledger, the Gemini monitor - read an empty environment and silently
chose its stub. A fully configured project reported `{"rail": "fake"}` for days.

The lesson these tests encode: a configuration layer that fails by returning
plausible defaults needs its *reporting* tested, not just its parsing.
"""

import pytest

from pocketchange import config

KEYS = ("GOOGLE_API_KEY", "GEMINI_API_KEY", "RAZORPAY_KEY_ID", "RAZORPAY_KEY_SECRET",
        "LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY")


@pytest.fixture
def clean(monkeypatch, tmp_path):
    # These tests are ABOUT load(), so the session-wide opt-out that keeps the
    # rest of the suite offline has to come off here - otherwise they would all
    # exercise the early return and prove nothing.
    monkeypatch.delenv("POCKETCHANGE_NO_DOTENV", raising=False)
    for k in KEYS:
        monkeypatch.delenv(k, raising=False)
    return tmp_path / ".env"


def test_the_offline_guard_stops_it_reading_anything(monkeypatch, tmp_path):
    """The guard the rest of the suite relies on. Without it, clearing the
    environment was pointless: load() runs inside every model invocation and put
    the credentials straight back."""
    monkeypatch.setenv("POCKETCHANGE_NO_DOTENV", "1")
    for k in KEYS:
        monkeypatch.delenv(k, raising=False)
    env = tmp_path / ".env"
    env.write_text("GEMINI_API_KEY=would-reach-the-network\n")

    assert config.load(env) == {"gemini": False, "razorpay": False, "langfuse": False}
    import os

    assert "GOOGLE_API_KEY" not in os.environ


def write(path, **pairs):
    path.write_text("\n".join(f"{k}={v}" for k, v in pairs.items()) + "\n")
    return path


# --- what it reports -------------------------------------------------------


def test_an_absent_file_reports_everything_missing(clean):
    assert config.load(clean) == {"gemini": False, "razorpay": False, "langfuse": False}


def test_a_populated_file_reports_everything_present(clean):
    write(clean, GEMINI_API_KEY="g", RAZORPAY_KEY_ID="rzp_test_x",
          RAZORPAY_KEY_SECRET="s", LANGFUSE_PUBLIC_KEY="p", LANGFUSE_SECRET_KEY="q")
    assert config.load(clean) == {"gemini": True, "razorpay": True, "langfuse": True}


def test_half_a_credential_pair_is_not_configured(clean):
    """An id without a secret is not usable, and must not read as ready."""
    write(clean, RAZORPAY_KEY_ID="rzp_test_x", LANGFUSE_PUBLIC_KEY="p")
    status = config.load(clean)
    assert status["razorpay"] is False
    assert status["langfuse"] is False


# --- the mirroring that everything downstream depends on -------------------


def test_gemini_key_is_mirrored_into_google_api_key(clean, monkeypatch):
    """ADK and google-genai both reach for GOOGLE_API_KEY. Every model call in
    this project would fail with only GEMINI_API_KEY set."""
    import os

    write(clean, GEMINI_API_KEY="the-key")
    config.load(clean)
    assert os.environ["GOOGLE_API_KEY"] == "the-key"


def test_loading_actually_puts_values_in_the_environment(clean, monkeypatch):
    """The bug was not parsing - it was that nobody called this."""
    import os

    write(clean, RAZORPAY_KEY_ID="rzp_test_abc", RAZORPAY_KEY_SECRET="shh")
    assert os.environ.get("RAZORPAY_KEY_ID") is None
    config.load(clean)
    assert os.environ["RAZORPAY_KEY_ID"] == "rzp_test_abc"


def test_the_fallback_parser_handles_quotes_comments_and_blanks(clean, monkeypatch):
    import os

    monkeypatch.setattr(config, "load", config.load)   # keep the real one
    clean.write_text(
        '# a comment\n\nRAZORPAY_KEY_ID="rzp_test_quoted"\n'
        "RAZORPAY_KEY_SECRET='single'\nnot a pair\n"
    )
    config._load_manually(clean)
    assert os.environ["RAZORPAY_KEY_ID"] == "rzp_test_quoted"
    assert os.environ["RAZORPAY_KEY_SECRET"] == "single"


# --- secrecy ---------------------------------------------------------------


def test_nothing_it_returns_or_prints_contains_a_secret(clean):
    write(clean, GEMINI_API_KEY="SUPER-SECRET-VALUE",
          RAZORPAY_KEY_ID="rzp_test_SECRET", RAZORPAY_KEY_SECRET="ALSO-SECRET")
    status = config.load(clean)
    assert set(status.values()) <= {True, False}

    line = config.report()
    for secret in ("SUPER-SECRET-VALUE", "rzp_test_SECRET", "ALSO-SECRET"):
        assert secret not in line
    assert "gemini:yes" in line
