"""Model construction: retries, and one quota bucket per parallel agent.

RabbitHole's models/llm.py is a provider factory across Groq, Gemini, Cerebras,
SambaNova and OpenRouter, and its perspective nodes alternate EVEN/ODD endpoints
"to prevent concurrent rate limits in parallel execution". That comment turned out
to be the single most useful line in the repo for us.

We have one provider, so the equivalent levers are two:

  * retry with backoff, for transient 429 and 503
  * a distinct model NAME per parallel agent, because free-tier quotas are
    enforced per model - six agents sharing one name queue behind one bucket

Neither rescues a *daily* cap. gemini-3.5-flash allows 20 generate_content calls
per day on the free tier, and one fan-out errand spends more than that alone,
which is why the lite tier leads the ordering.
"""

from __future__ import annotations

import json

from google.adk.models import Gemini
from google.genai import types

# 5 attempts from 2s, doubling to a 60s ceiling. Covers a 429's typical ~15-25s
# retry-after and rides out a short capacity spike without hanging a demo.
RETRY = types.HttpRetryOptions(
    attempts=5,
    initial_delay=2.0,
    max_delay=60.0,
    exp_base=2.0,
    http_status_codes=[429, 500, 502, 503, 504],
)


def resilient(model_name: str) -> Gemini:
    """A Gemini model that survives rate limits and capacity spikes."""
    return Gemini(model=model_name, retry_options=RETRY)


def fleet(count: int) -> tuple[str, ...]:
    """One model name per agent, so each draws on its own quota."""
    from pocketchange import config

    return config.spread_models(count)


# --- the chain idiom ------------------------------------------------------
#
# RabbitHole writes a node's model call as
#
#     chain = ChatPromptTemplate.from_messages([("system", PROMPT)]) \
#             | MODEL.with_structured_output(Schema)
#     result = chain.invoke({"topic": ...})
#
# built once at module scope and invoked inside the node. That shape is worth
# keeping - the prompt, the model and the output schema are declared together and
# read as one thing - but it is LangChain, and we are on google-genai.
#
# StructuredChain is the same idiom against genai's response_schema, so node code
# below looks like node code there.

from dataclasses import dataclass

from pydantic import BaseModel


@dataclass
class StructuredChain:
    """A system prompt bound to a model and a response schema.

    `invoke(variables)` formats the prompt, calls the model, and returns a
    validated pydantic object - never a string that still needs parsing.
    """

    system: str
    schema: type[BaseModel]
    model: str = "gemini-3.5-flash-lite"
    human: str = ""
    max_output_tokens: int = 2048
    # "judge" routes to the stronger tier when one is configured.
    tier: str = "work"
    timeout_ms: int = 45_000

    def invoke(self, variables: dict) -> BaseModel:
        from google import genai
        from google.genai import types as genai_types

        from pocketchange import config

        config.load()
        prompt = self.system.format(**variables)
        if self.human:
            prompt = f"{prompt}\n\n{self.human.format(**variables)}"

        try:
            return self._gemini(prompt, genai, genai_types)
        except Exception as primary:  # noqa: BLE001
            from pocketchange import providers

            if not providers.configured():
                raise
            try:
                return self._fallback(prompt)
            except providers.NoProviderAnswered:
                raise primary

    def _gemini(self, prompt: str, genai, genai_types) -> BaseModel:
        import os

        from pocketchange import providers

        client, model, _flavour = providers.gemini_client(self.model, tier=self.tier)
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=self.schema,
                # A ceiling on the reply, because without one this model
                # occasionally runs away: a 21 KB response was observed in which
                # a free-text field rambled for pages and the actual structured
                # list came back empty. Truncation makes that invalid JSON, which
                # raises here and gets retried - far better than a degenerate
                # answer arriving as a confident, well-formed empty result.
                max_output_tokens=self.max_output_tokens,
                # A timeout, because a hang is not an exception. A run whose
                # decompose call never returns simply stops growing: no error,
                # no terminal event, and a console that cannot tell "thinking"
                # from "dead". Observed at 75 seconds and still climbing.
                http_options=genai_types.HttpOptions(
                    retry_options=RETRY, timeout=self.timeout_ms),
            ),
        )
        parsed = getattr(response, "parsed", None)
        if parsed is not None:
            return parsed
        # genai returns text when it cannot parse; surface that rather than
        # handing a half-built object downstream.
        return self.schema.model_validate_json(response.text)

    def _fallback(self, prompt: str) -> BaseModel:
        """Ask somewhere else. Gemini's 15-per-minute tier is the binding limit.

        The schema is described in the prompt rather than enforced by the API,
        because these providers do not take a pydantic model - so the answer is
        still validated here, and a provider that returns the wrong shape fails
        exactly like one that returned nothing.
        """
        from pocketchange import providers

        schema_hint = json.dumps(self.schema.model_json_schema())
        asked = (f"{prompt}\n\nReply with a single JSON object matching this "
                 f"JSON Schema. No prose, no code fence.\n{schema_hint}")
        name, raw = providers.json_chat(asked, max_tokens=self.max_output_tokens)
        body = raw.strip()
        if body.startswith("```"):
            body = body.split("```")[1].removeprefix("json").strip()
        return self.schema.model_validate_json(body)
