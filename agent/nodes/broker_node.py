"""The broker, and the payers it creates.

The one agent here that alters the authority graph rather than acting inside it.
It holds `delegate` and mints a `pay` mandate per seller, each capped at that
seller's subtotal.

A caveat worth carrying in the code rather than only in a doc: the broker's token
necessarily also permits `pay`, because attenuation is monotonic and a token
cannot confer a capability it lacks. The broker is stopped from spending by the
gateway, on identity - see `pocketchange.token.is_broker`. The per-seller caps are
cryptographic; the broker/payer split is policy.
"""

from __future__ import annotations

from google.adk.agents import LlmAgent

from agent.models import resilient
from agent.prompts import BROKER_INSTRUCTION, SUBPAYER_INSTRUCTION
from agent.tools import ToolSurface


def broker_node(tools: ToolSurface, model_name: str) -> LlmAgent:
    """Splits the chosen cart and mints one mandate per seller."""
    return LlmAgent(
        name="broker",
        model=resilient(model_name),
        description="Splits a cart by seller and mints a capped mandate for each.",
        instruction=BROKER_INSTRUCTION,
        tools=tools.broker_functions(),
    )


def sub_payer_node(tools: ToolSurface, model_name: str) -> LlmAgent:
    """Pays each seller with that seller's own narrow mandate."""
    return LlmAgent(
        name="sub_payer",
        model=resilient(model_name),
        description="Settles each seller's share using its own capped mandate.",
        instruction=SUBPAYER_INSTRUCTION,
        tools=tools.sub_payer_functions(),
    )
