"""Graph assembly. RabbitHole's builder.py, expressed in ADK.

    LoopAgent(max_iterations=3)          <- the cycle
      ParallelAgent "market"             <- fan-out
        shopper_thrifty                     each on its own model quota
        shopper_complete
        shopper_balanced
      chooser                            <- fan-in, and the actual decision
      payer
      reviewer                           <- routing: done | continue | give_up

RabbitHole builds edges explicitly because LangGraph needs them. ADK expresses the
same topology through composition - LoopAgent runs its sub-agents in order and
repeats, ParallelAgent runs its own concurrently - so the graph is the nesting.

What is deliberately *not* in the agent's hands: whether a refusal is retryable.
That is graph/route.py, ordinary testable code, because a model that decides to
retry a scope refusal wastes rounds it cannot win.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from google.adk.agents import LoopAgent, ParallelAgent
from google.adk.runners import InMemoryRunner
from google.genai import types

from agent.models import fleet
from agent.nodes import (
    all_shoppers,
    broker_node,
    chooser_node,
    payer_node,
    reviewer_node,
    sub_payer_node,
)
from agent.prompts import STRATEGY_BRIEFS
from agent.tools import ToolSurface
from agent.utils import Progress

from .route import classify, route_after_refusal
from .state import ErrandState

MAX_ROUNDS = 3


@dataclass
class ErrandResult:
    """What one errand did, across every round."""

    transcript: list[str]
    tools: ToolSurface
    rounds: int
    progress: Progress

    @property
    def paid(self) -> bool:
        return any(a.allowed for a in self.tools.attempted("checkout"))

    @property
    def refusals(self) -> int:
        return sum(1 for a in self.tools.attempted("checkout") if not a.allowed)

    @property
    def replanned(self) -> bool:
        """Recovered from a refusal, rather than stopping at one."""
        return self.refusals > 0 and self.paid

    @property
    def proposals_seen(self) -> int:
        return len(self.tools.attempted("propose_cart"))

    @property
    def payout_attempts(self) -> int:
        return len(self.tools.attempted("payout"))

    @property
    def payouts_succeeded(self) -> int:
        return sum(a.allowed for a in self.tools.attempted("payout"))

    @property
    def refusal_kind(self) -> str:
        return classify(self.tools.last_refusal)

    @property
    def recommended_action(self) -> str:
        """What routing says should happen next, independent of the model."""
        return route_after_refusal(
            self.tools.last_refusal,
            remaining_paise=self.tools.remaining_paise,
            iteration=self.rounds,
            max_rounds=MAX_ROUNDS,
        )

    def state(self) -> ErrandState:
        return self.tools.snapshot()

    def summary(self) -> dict[str, Any]:
        return {
            "paid": self.paid,
            "refusals": self.refusals,
            "replanned": self.replanned,
            "rounds": self.rounds,
            "proposals": self.proposals_seen,
            "chosen": self.tools.chosen_strategy,
            "why": self.tools.choice_reason,
            "refusal_kind": self.refusal_kind,
            "outcome": self.tools.outcome,
            "cart": dict(self.tools.cart),
            "payout_attempts": self.payout_attempts,
            "payouts_succeeded": self.payouts_succeeded,
        }


def build_buyer(tools: ToolSurface, model: str | None = None) -> LoopAgent:
    """Assemble the graph.

    Passing `model` puts every agent on that one model - correct on a paid key,
    wrong on the free tier, where six agents sharing a name share a bucket.
    """
    count = len(STRATEGY_BRIEFS) + 3
    models = fleet(count) if model is None else tuple([model] * count)

    market = ParallelAgent(
        name="market",
        description="Shoppers price the same request against one budget.",
        sub_agents=all_shoppers(tools, models[: len(STRATEGY_BRIEFS)]),
    )

    # With a broker token the purchase is split per seller and each share is paid
    # under its own capped mandate. Without one, a single payer settles the whole
    # cart - the older single-seller path, kept so a surface without delegation
    # authority still works.
    settle = (
        [broker_node(tools, models[-3]), sub_payer_node(tools, models[-2])]
        if tools.broker_token
        else [payer_node(tools, models[-2])]
    )

    return LoopAgent(
        name="buyer",
        description="Shops in parallel, chooses, delegates per seller, and re-plans.",
        sub_agents=[
            market,
            chooser_node(tools, models[-3]),
            *settle,
            reviewer_node(tools, models[-1]),
        ],
        max_iterations=MAX_ROUNDS,
    )


async def run_errand(
    tools: ToolSurface,
    request: str,
    model: str | None = None,
    on_event=None,
) -> ErrandResult:
    """Run to completion, to an unrecoverable refusal, or to MAX_ROUNDS."""
    progress = Progress(sink=on_event)
    buyer = build_buyer(tools, model)
    runner = InMemoryRunner(agent=buyer, app_name="pocketchange")
    session = await runner.session_service.create_session(
        app_name="pocketchange", user_id="buyer"
    )

    transcript: list[str] = []
    message = types.Content(role="user", parts=[types.Part(text=request)])

    async for event in runner.run_async(
        user_id="buyer", session_id=session.id, new_message=message
    ):
        if not (event.content and event.content.parts):
            continue
        for part in event.content.parts:
            text = getattr(part, "text", None)
            if not text or not text.strip():
                continue
            line = f"[{event.author}] {text.strip()}"
            transcript.append(line)
            progress(line)

    return ErrandResult(
        transcript=transcript, tools=tools, rounds=tools.iteration, progress=progress
    )
