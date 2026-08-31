"""StructuredChain: the model boundary, previously untested.

It gained two guards this week after a live failure, and neither was covered:

  max_output_tokens  the model emitted 21 KB in which a free-text field ran away
                     and the structured list came back empty. The funnel read
                     that as "this task is atomic" and paid the whole budget in
                     one transaction using the root mandate.
  timeout            a hang is not an exception. A decompose call that never
                     returns leaves a run silently not growing.

No model is called here; the client is stubbed.
"""

import sys
import types

import pytest
from pydantic import BaseModel, Field

from agent.models.llm import StructuredChain


class Answer(BaseModel):
    items: list[str] = Field(default_factory=list)
    note: str = ""


@pytest.fixture
def genai(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "not-a-real-key")
    captured = {}

    class Models:
        def generate_content(self, *, model, contents, config):
            captured["model"] = model
            captured["prompt"] = contents
            captured["config"] = config
            return types.SimpleNamespace(parsed=captured.get("parsed"),
                                         text=captured.get("text"))

    class Client:
        def __init__(self, **_):
            self.models = Models()

    genai_mod = types.ModuleType("google.genai")
    genai_mod.Client = Client

    class _Types:
        class GenerateContentConfig(dict):
            def __init__(self, **kw):
                super().__init__(**kw)
                self.__dict__.update(kw)

        class HttpOptions(dict):
            def __init__(self, **kw):
                super().__init__(**kw)
                self.__dict__.update(kw)

    genai_mod.types = _Types
    types_mod = types.ModuleType("google.genai.types")
    types_mod.GenerateContentConfig = _Types.GenerateContentConfig
    types_mod.HttpOptions = _Types.HttpOptions

    google = sys.modules.get("google") or types.ModuleType("google")
    monkeypatch.setitem(sys.modules, "google", google)
    monkeypatch.setitem(sys.modules, "google.genai", genai_mod)
    monkeypatch.setitem(sys.modules, "google.genai.types", types_mod)
    monkeypatch.setattr(google, "genai", genai_mod, raising=False)
    return captured


def chain(**kw):
    return StructuredChain(system="Do {thing}.", schema=Answer, **kw)


# --- the two guards --------------------------------------------------------


def test_a_reply_ceiling_is_always_sent(genai):
    """Without one, a runaway reply arrives as a well-formed empty answer."""
    genai["parsed"] = Answer(items=["a"])
    chain().invoke({"thing": "something"})
    assert genai["config"].max_output_tokens > 0


def test_a_timeout_is_always_sent(genai):
    genai["parsed"] = Answer()
    chain().invoke({"thing": "something"})
    http = genai["config"].http_options
    assert http.timeout > 0
    assert http.retry_options is not None


def test_both_ceilings_are_configurable(genai):
    genai["parsed"] = Answer()
    chain(max_output_tokens=99, timeout_ms=1234).invoke({"thing": "x"})
    assert genai["config"].max_output_tokens == 99
    assert genai["config"].http_options.timeout == 1234


# --- parsing ---------------------------------------------------------------


def test_a_parsed_object_is_returned_directly(genai):
    genai["parsed"] = Answer(items=["one", "two"])
    assert chain().invoke({"thing": "x"}).items == ["one", "two"]


def test_unparsed_text_is_validated_rather_than_half_trusted(genai):
    genai["parsed"] = None
    genai["text"] = '{"items": ["three"], "note": "ok"}'
    assert chain().invoke({"thing": "x"}).items == ["three"]


def test_unusable_text_raises_instead_of_returning_an_empty_answer(genai):
    """This is the important one. Returning Answer() here is exactly how a
    truncated runaway became a confident 'nothing to divide'."""
    genai["parsed"] = None
    genai["text"] = "the model started explaining itself and never stopped"
    with pytest.raises(Exception):
        chain().invoke({"thing": "x"})


# --- prompt assembly -------------------------------------------------------


def test_the_human_turn_is_appended_and_both_are_formatted(genai):
    genai["parsed"] = Answer()
    StructuredChain(system="System: {thing}.", human="Now do {thing}.",
                    schema=Answer).invoke({"thing": "the split"})
    assert genai["prompt"] == "System: the split.\n\nNow do the split."


# --- somewhere else to ask --------------------------------------------------


def test_a_dead_primary_falls_back_and_still_validates(genai, monkeypatch):
    from pocketchange import providers

    genai["raises"] = RuntimeError("429 RESOURCE_EXHAUSTED")

    class Models:
        def generate_content(self, **kw):
            raise RuntimeError("429 RESOURCE_EXHAUSTED")

    import sys
    sys.modules["google.genai"].Client = lambda **kw: type("C", (), {"models": Models()})()
    monkeypatch.setenv("GROQ_API_KEY", "g")
    monkeypatch.setattr(providers, "json_chat",
                        lambda prompt, **kw: ("groq", '{"items": ["from groq"], "note": "ok"}'))

    assert chain().invoke({"thing": "x"}).items == ["from groq"]


def test_a_fallback_returning_the_wrong_shape_fails_like_no_answer(genai, monkeypatch):
    """These providers take no schema, so the answer is validated here. A wrong
    shape must not slip through as a half-built object."""
    from pocketchange import providers

    class Models:
        def generate_content(self, **kw):
            raise RuntimeError("down")

    import sys
    sys.modules["google.genai"].Client = lambda **kw: type("C", (), {"models": Models()})()
    monkeypatch.setenv("GROQ_API_KEY", "g")
    monkeypatch.setattr(providers, "json_chat",
                        lambda prompt, **kw: ("groq", '{"items": "not a list"}'))

    with pytest.raises(Exception):
        chain().invoke({"thing": "x"})
