"""Test-wide isolation.

Every gateway built in a test gets its own root key. Without this the persisted
key is shared, two gateways verify each other's tokens, and a forgery test
quietly stops testing forgery - which is exactly what happened when key
persistence was added: the assertion moved from 401 forged to 404 unknown
mandate and would have gone unnoticed if the suite had not been re-run.

Tests must also never write a key to the repository.
"""

import os

import pytest


@pytest.fixture(autouse=True)
def ephemeral_keys(monkeypatch):
    monkeypatch.setenv("POCKETCHANGE_EPHEMERAL_KEYS", "1")


@pytest.fixture(autouse=True, scope="session")
def never_read_dotenv():
    """Stop config.load() undoing the scrubbing below.

    It is called again inside every model invocation, so clearing the
    environment was not enough: a test that believed it was offline would have
    its credentials restored from .env and quietly reach the network.
    """
    os.environ["POCKETCHANGE_NO_DOTENV"] = "1"
    yield
    os.environ.pop("POCKETCHANGE_NO_DOTENV", None)


@pytest.fixture(autouse=True)
def no_cloud(monkeypatch):
    """No credentials in tests, so nothing reaches DynamoDB, Razorpay or Bedrock.

    Clearing the environment is NOT sufficient for AWS and this is the trap the
    port walked into. boto3 resolves credentials from a chain - `~/.aws/config`,
    an SSO cache, instance metadata - none of which is an environment variable,
    so on any developer machine with `aws configure` already run,
    `bedrock.available()` kept answering True with an empty environment and the
    suite quietly went back on the network.

    POCKETCHANGE_NO_BEDROCK is the switch that actually closes it, checked
    before boto3 is consulted at all. POCKETCHANGE_NO_SECRETS_MANAGER is the
    same switch for secrets.py, added when the root key gained a third tier -
    without it, a suite run on a machine with both AWS credentials and
    POCKETCHANGE_KEY_SECRET_NAME set in its shell profile would quietly start
    minting or fetching a real key on every test.
    """
    monkeypatch.setenv("POCKETCHANGE_NO_BEDROCK", "1")
    monkeypatch.setenv("POCKETCHANGE_NO_DYNAMODB", "1")
    monkeypatch.setenv("POCKETCHANGE_NO_SECRETS_MANAGER", "1")
    for name in (
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
        "AWS_PROFILE",
        "RAZORPAY_KEY_ID",
        "RAZORPAY_KEY_SECRET",
        # The fallback providers. Omitting these was not hypothetical: adding the
        # fallback chain immediately turned two "the model is unreachable" tests
        # into live calls to Groq, which passed for the wrong reason and put the
        # suite back on the network.
        "GROQ_API_KEY",
        "OPENROUTER_API_KEY",
        "CEREBRAS_API_KEY",
        "SAMBANOVA_API_KEY",
        "TAVILY_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)
