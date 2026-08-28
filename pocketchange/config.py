"""Environment loading and credential normalisation.

Google hands out API keys under two different names depending on where you got
them. AI Studio calls it GEMINI_API_KEY; Google Cloud calls it GOOGLE_API_KEY.
They are not interchangeable in practice - a Cloud key only works if the
Generative Language API is enabled on that project, while an AI Studio key
arrives working.

So GEMINI_API_KEY wins when both are present. A key that came from AI Studio is
the one more likely to function, and silently preferring a broken Cloud key
produces a PERMISSION_DENIED that looks like a code fault.
"""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env"


def load(env_file: Path | None = None) -> dict[str, bool]:
    """Load .env and normalise credential names. Returns what is configured.

    Never returns or logs a value - only whether each one is present. Secrets
    that reach a log are secrets that have been disclosed.
    """
    # An explicit opt-out, for tests. conftest.py scrubs credentials from the
    # environment so the suite cannot reach the network - and then this function
    # helpfully put them straight back, because it is called again inside every
    # model invocation. A test that believes it is offline and is not is worse
    # than no isolation at all: it is slow, it spends quota, and it passes for
    # reasons nobody intended.
    if os.getenv("POCKETCHANGE_NO_DOTENV"):
        return _status()

    path = env_file or ENV_FILE
    if path.exists():
        try:
            from dotenv import load_dotenv

            load_dotenv(path)
        except ImportError:
            _load_manually(path)

    gemini = os.getenv("GEMINI_API_KEY", "").strip()
    if gemini:
        # ADK and google-genai both look for GOOGLE_API_KEY first, so mirror the
        # working key into it rather than teaching every call site about both.
        os.environ["GOOGLE_API_KEY"] = gemini

    return _status()


def _status() -> dict[str, bool]:
    return {
        "gemini": bool(os.getenv("GOOGLE_API_KEY")),
        "razorpay": bool(os.getenv("RAZORPAY_KEY_ID") and os.getenv("RAZORPAY_KEY_SECRET")),
        "langfuse": bool(os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")),
    }


def _load_manually(path: Path) -> None:
    """Minimal .env parser, so config never hard-depends on python-dotenv."""
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def report() -> str:
    """One line naming what is configured. Safe to print."""
    status = load()
    return "  ".join(f"{k}:{'yes' if v else 'NO'}" for k, v in status.items())


# Gemini 3.5+ is an ATA requirement, so every candidate here clears that bar.
# Ordered by preference: the flash tier for the buyer's reasoning, lite as the
# fallback. Google returns 503 on a model that exists but is at capacity, which
# is transient and worth stepping past rather than crashing on.
# Lite first, deliberately. On the free tier gemini-3.5-flash carries a *daily*
# cap of 20 generate_content requests, and one multi-agent errand spends more than
# that on its own - three agents, up to three rounds, several turns each. The lite
# tier's limits are far higher. Retry logic cannot rescue a daily quota, so the
# ordering has to.
BUYER_MODELS = ("gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-3.7-flash")

# The monitor is meant to be the cheap trusted model of the AI-control pattern,
# so lite is the right default rather than a compromise.
MONITOR_MODELS = ("gemini-3.5-flash-lite", "gemini-3.5-flash")

# Quotas are enforced PER MODEL, so parallel agents sharing one model name share
# one bucket and burst straight through it. RabbitHole spreads across alternating
# endpoints and five providers for exactly this reason; with a single provider the
# equivalent lever is distinct model names, one per parallel node.
SHOPPER_MODELS = (
    "gemini-3.5-flash-lite",
    "gemini-flash-lite-latest",
    "gemini-3.1-flash-lite",
)


def spread_models(count: int) -> tuple[str, ...]:
    """One model name per parallel agent, so each draws on its own quota.

    Falls back to repeating the list if more agents are asked for than there are
    distinct models - degraded, but never wrong.
    """
    if count <= 0:
        return ()
    pool = SHOPPER_MODELS
    return tuple(pool[i % len(pool)] for i in range(count))


_RESOLVED: dict[tuple, str] = {}


def resolve_model(candidates: tuple[str, ...], *, override_env: str | None = None) -> str:
    """First candidate that actually answers, or the last one as a fallback.

    Probes with a one-token request. An explicit override skips probing entirely -
    if someone names a model, they get that model rather than a silent substitution.
    """
    if override_env:
        chosen = os.getenv(override_env, "").strip()
        if chosen:
            return chosen

    # Probing costs a real generate_content call, and on a 15-per-minute free tier
    # those are the same calls the agents need. Resolve once per process.
    cached = _RESOLVED.get(candidates)
    if cached:
        return cached

    load()
    if not os.getenv("GOOGLE_API_KEY"):
        return candidates[-1]

    try:
        from google import genai

        client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    except Exception:  # noqa: BLE001
        return candidates[-1]

    for name in candidates:
        try:
            client.models.generate_content(model=name, contents="ok")
            _RESOLVED[candidates] = name
            return name
        except Exception:  # noqa: BLE001
            continue
    _RESOLVED[candidates] = candidates[-1]
    return candidates[-1]
