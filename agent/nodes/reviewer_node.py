"""The reviewer: does this errand continue, and if so how?

RabbitHole routes after its HITL node by reading state. Here the routing rule
lives in graph/route.py as ordinary code, and the reviewer is handed its verdict
rather than asked to infer one - so a scope refusal can never be retried because
a model felt optimistic.
"""

from __future__ import annotations

from google.adk.agents import LlmAgent

from agent.models import resilient
from agent.prompts import REVIEWER_INSTRUCTION
from agent.tools import ToolSurface


def reviewer_node(tools: ToolSurface, model_name: str) -> LlmAgent:
    return LlmAgent(
        name="reviewer",
        model=resilient(model_name),
        description="Decides whether the errand is finished or should re-plan.",
        instruction=REVIEWER_INSTRUCTION,
        tools=tools.reviewer_functions(),
    )
