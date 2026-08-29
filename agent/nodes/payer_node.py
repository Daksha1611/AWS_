"""The payer. Holds the pay capability, never sees a product description.

The separation is structural rather than a matter of instruction: the payer's
token is a sibling of the shoppers', not a descendant, so it could not read a
listing and act on it even if it wanted to.
"""

from __future__ import annotations

from google.adk.agents import LlmAgent

from agent.models import resilient
from agent.prompts import PAYER_INSTRUCTION
from agent.tools import ToolSurface


def payer_node(tools: ToolSurface, model_name: str) -> LlmAgent:
    return LlmAgent(
        name="payer",
        model=resilient(model_name),
        description="Settles the adopted cart.",
        instruction=PAYER_INSTRUCTION,
        tools=tools.payer_functions(),
    )
