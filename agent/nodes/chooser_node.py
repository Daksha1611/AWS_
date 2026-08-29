"""The chooser: RabbitHole's judiciary, deciding between carts.

Three shoppers propose; one agent adopts. This is where the trade-off is actually
resolved, and it is the decision that makes the system an agent rather than a
pipeline - the outcome depends on judgement, not on ordering.

Never reads a listing. It sees totals, item counts and rationales.
"""

from __future__ import annotations

from google.adk.agents import LlmAgent

from agent.models import resilient
from agent.prompts import CHOOSER_INSTRUCTION
from agent.tools import ToolSurface


def chooser_node(tools: ToolSurface, model_name: str) -> LlmAgent:
    return LlmAgent(
        name="chooser",
        model=resilient(model_name),
        description="Compares competing carts against the budget and adopts one.",
        instruction=CHOOSER_INSTRUCTION,
        tools=tools.chooser_functions(),
    )
