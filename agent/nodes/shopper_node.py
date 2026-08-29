"""The shoppers. Three strategies, one request, run concurrently.

RabbitHole's perspective_node.py parameterises one function over ten ids and
exports p1_node..p10_node. Same shape here over three strategies - the node is one
function, the strategies are data, and the graph wires whichever it wants.

Trust position: these are the only agents that read seller-controlled product
descriptions, and they hold no payment capability. Widening the fan-out widens the
untrusted layer without widening its authority, which is exactly what sibling
delegation was chosen to make possible.
"""

from __future__ import annotations

from google.adk.agents import LlmAgent

from agent.models import resilient
from agent.prompts import STRATEGY_BRIEFS, shopper_instruction
from agent.tools import ToolSurface


def shopper_node(tools: ToolSurface, strategy: str, model_name: str) -> LlmAgent:
    """One shopper, bound to one strategy and its own model quota."""
    if strategy not in STRATEGY_BRIEFS:
        raise KeyError(f"unknown strategy: {strategy}. Known: {sorted(STRATEGY_BRIEFS)}")
    return LlmAgent(
        name=f"shopper_{strategy}",
        model=resilient(model_name),
        description=f"Assembles a cart, optimising for: {STRATEGY_BRIEFS[strategy][:60]}",
        instruction=shopper_instruction(strategy),
        tools=tools.shopper_functions(),
    )


def all_shoppers(tools: ToolSurface, models: tuple[str, ...]) -> list[LlmAgent]:
    """One shopper per strategy, each on a different model name."""
    return [
        shopper_node(tools, strategy, models[i % len(models)])
        for i, strategy in enumerate(STRATEGY_BRIEFS)
    ]
