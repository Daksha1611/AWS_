# Porting Pocket Change to AWS

Working notes for the move off Google Cloud. Same rule as `hey.md`: write down the
*reasoning*, not just the outcome, because in three weeks the outcome will be
obvious from the code and the reasoning will not.

Read this before changing anything in `pocketchange/bedrock.py`, `agent/`,
`pocketchange/policy.py` or the storage backends — several of the choices below
look arbitrary until you know what was tried first.

---

## 0. Why any of this

The project was built against Gemini, Vertex, Firestore and Cloud Run because a
previous event required a Google Cloud service. None of that was load-bearing:
the thing the project actually claims — that enforcement is separable from the
reasoning layer — is a claim about the gateway, not about who hosts the model.

So the port is a test of the claim. If swapping the model provider, the agent
framework and the database required touching `pocketchange/token.py`,
`ledger.py` or the `/pay` decision path, then enforcement was never really
separate and the project's headline was decoration.

It mostly did not. What did have to change is listed in §3.

---

## 1. Track: Build It, not Ship It

**Decision.** Target the open-source track and run entirely locally.

**Why.** Build It is scored on AWS *open-source* usage — Strands Agents SDK,
Cedar, SAM CLI + LocalStack, OpenSearch — and explicitly needs no deployment and
no AWS account. Ship It requires a live URL, which is the one thing we are not
doing. The two tracks are judged with equal care, so there is no penalty for
staying local.

It also happens to fit what the repo already had: `agent/strands_buyer.py`
existed before the port as a second agent framework used to prove the gateway
was framework-agnostic. That file stops being an experiment and becomes the
main path.

---

## 2. Decisions

### D1 — Amazon Bedrock replaces the Gemini / Vertex pair

The old path had two doors to the same models: an AI Studio API key and a Vertex
project, with a documented preference order between them. Both are gone.

**Why Bedrock, beyond "it is the AWS one".** The old primary authenticated with a
bare API key belonging to whoever pasted it into `.env`. For a project whose
subject is *bounded authority*, having the trusted monitor authenticate with a
shared secret that no one administers was an embarrassment hiding in plain
sight. Bedrock signs with the ordinary AWS credential chain, so the model is
reached the same way the ledger's table is — an IAM principal, a region, and a
policy that can be read and scoped to named model ids.

**Client.** `AnthropicBedrockMantle` from the `anthropic` SDK rather than raw
`boto3` `bedrock-runtime`. It is the documented Messages-API path onto Bedrock
and it gives schema-enforced structured output (`messages.parse`), which is
exactly what `StructuredChain` was hand-rolling with a JSON-schema hint in the
prompt. `boto3` is still a dependency — Strands and DynamoDB use it.

### D2 — Three model tiers, and the monitor gets the smallest

`WORK_MODEL` for the buyer's reasoning, `SHOPPER_MODEL` for the parallel
fan-out, `JUDGE_MODEL` for the monitor.

This mirrors the old flash/flash-lite split, but the reason is different and
worth stating plainly: the monitor is small **by design**, not to save money.
It is the trusted component in an AI-control arrangement and it answers one
narrow question. A trusted layer should be simple enough to reason about.

### D3 — `spread_models()` keeps its shape but loses its trick

The old implementation returned a *different* model name per parallel agent,
because the free tier metered quota per model name and six agents sharing one
name queued behind one bucket. That was a real finding and a good hack.

It buys nothing on Bedrock, which meters per account and region. Returning
distinct model ids now would spread load across models of *different
capability* for no benefit — strictly worse. So the function returns the same
shopper model N times and throttling is handled by SDK retry, where it belongs.

The signature stays because the graph builder asks for one id per agent, and a
genuine tier split (a stronger model for one strategy) would live here.

### D4 — Region defaults to `us-east-1`, not `ap-south-1`

Every price in this project is in paise and the old Vertex location was
`asia-south1`, so Mumbai is the sentimental choice. Bedrock model availability
is not uniform across regions, and a demo that dies because a model is not
served in `ap-south-1` dies for a reason that has nothing to do with what is
being demonstrated. Overridable via `POCKETCHANGE_BEDROCK_REGION`.

Model ids may also need a geography prefix (`us.`, `eu.`, `apac.`) when the
region serves them through a cross-region inference profile. Which one is a
property of the account, not of the code, so every id is overridable and the
error is allowed to surface rather than being guessed at.

### D5 — Strands Agents SDK replaces google-adk

*(in progress — see §3 for status)*

`LlmAgent` → `strands.Agent`, and ADK's `LoopAgent` / `ParallelAgent`
composition → an explicit orchestrator. The nodes were always thin: name, model,
description, instruction, tools. The topology lived in `builder.py` and moves
there too.

### D6 — Cedar for the policy layer at `/pay`

*(in progress)*

Step 4b of the money path already carried this comment: *"The token cannot
express 'may grant but not spend', so the enforcement point does. Said plainly
because the distinction matters: the per-seller caps below are a cryptographic
guarantee; this line is a rule we chose to apply here."*

That is a policy language asking to exist. Cedar is exactly that, it is AWS
open-source, and it separates the two guarantees the code was already careful to
distinguish — attenuation stays cryptographic in the token, and the rules we
*chose* become readable, testable policy instead of `if` statements buried in a
2000-line module.

### D7 — DynamoDB replaces Firestore

*(in progress)*

`ledger.py` already documented Firestore as a poor fit: the mandate row is a hot
document, and Firestore's least favourite pattern is one sustained write per
second to the same document. DynamoDB's conditional writes and atomic `ADD` are
a *better* fit for a ledger than what was there before — the budget check and
the decrement become one conditional update, which is the invariant the
two-phase reservation exists to protect.

Runs locally against DynamoDB Local / LocalStack, so no AWS account is needed.

### D8 — The repository is no longer a fork

GitHub offers no self-service way to detach a fork, so the repo was rebuilt: the
fork was renamed aside, a fresh non-fork repository was created under the same
name, and the full history was pushed to it. Every commit and its authorship is
preserved.

### D9 — `LICENSE` and `NOTICE` added

`pyproject.toml` declared Apache-2.0 but no licence file existed, which means the
code was technically all-rights-reserved. Added the Apache-2.0 text and a
`NOTICE` recording the original authorship.

---

## 3. Changed files

### The model boundary

| File | Change | Why |
|---|---|---|
| `PORTING.md` | new | This file. |
| `pocketchange/bedrock.py` | new | Bedrock client, the three model tiers, schema-enforced structured output, and the `available()` check `/status` polls. Replaces the old two-door provider selection. |
| `pocketchange/providers.py` | trimmed | Lost `gemini_client`, `vertex_available` and the Vertex constants. The OpenAI-compatible fallback chain stays — see the file's own docstring for why it survives a port that removed its original reason. |
| `pocketchange/config.py` | rewritten | Deleted the credential mirroring. The old provider issued keys under two non-interchangeable names, so `load()` had to guess which one worked. Bedrock has no key. |
| `pocketchange/monitor.py` | `GeminiMonitor` → `BedrockMonitor` | The trusted layer now signs with the AWS credential chain, and runs on the smallest tier deliberately. |
| `pocketchange/gateway.py` | consolidated | Five inlined "do we have a model" environment checks became one `have_model()` over `bedrock.available()`. **They had drifted** — two looked for a project id and two did not, so one process could report a model on `/status` and refuse to use one on `/runs`. Capability strings now read `bedrock`. |
| `pocketchange/tracing.py` | `instrument_adk` → `instrument_agents` | Strands emits OTel GenAI conventions itself; one fewer package in between. |

### The agent layer

| File | Change | Why |
|---|---|---|
| `agent/runtime.py` | new | One place that knows how a node becomes a Strands agent, so node modules stay a name, a brief and a tool list. |
| `agent/models/llm.py` | rewritten | `StructuredChain` now calls Bedrock with the schema *enforced* rather than described in the prompt. Both live-failure guards (reply ceiling, timeout) survive. |
| `agent/graph/builder.py` | rewritten | ADK expressed the loop and the fan-out through class composition; Strands has no equivalent, so the topology is an explicit loop over a `Buyer` of `Stage`s. The shape is now inspectable without a model, which is what the assembly tests assert on. |
| `agent/nodes/*.py` | ported | `LlmAgent(...)` → `build_agent(...)`. The five affected nodes were always thin. |
| `agent/buyer.py` | ported | Also dropped model probing: the old provider needed a live one-token call to find which model name answered that day. |
| `agent/tools.py` | `finish()` lost `tool_context` | It existed only to set an escalation flag that broke out of ADK's loop. The loop is ordinary Python now and reads `tools.finished` — so an agent can no longer end an errand in a way no test could observe. |

### Tests

| File | Change | Why |
|---|---|---|
| `tests/conftest.py` | hardened | **The trap of the port.** Clearing `AWS_*` does not take a process offline — boto3 also reads `~/.aws/config`, an SSO cache and instance metadata. On any machine where `aws configure` had been run, the suite quietly went back on the network. `POCKETCHANGE_NO_BEDROCK` is checked before boto3 is consulted at all. |
| `tests/test_bedrock.py` | new | Availability, region precedence, and the model-spreading reversal. |
| `tests/test_llm.py` | rewritten | Stubs one function instead of installing a fake module tree into `sys.modules` — itself an argument for keeping the model boundary narrow. |
| `tests/test_monitor.py` | rewritten | Same, plus a new assertion that an unconfigured monitor declares it cannot judge. |
| `tests/test_config.py` | trimmed | The credential-mirroring tests had nothing left to test. |
| `tests/test_graph.py` | inverted | `test_every_agent_gets_its_own_quota` became `test_every_agent_draws_on_the_same_model`. See D3. |
| `frontend/{app,main}.js`, `index.html` | updated | Capability strings and the model line; the test-count stat the suite asserts against. |
| `pyproject.toml` | updated | `boto3` is a hard dependency now (the health check needs it). `gcp` and the ADK extras are gone; `agent` and `policy` extras replace them. |

---

## 4. What deliberately did not change

- `pocketchange/token.py` — attenuation, signing, verification. Untouched.
- `pocketchange/ledger.py` reservation semantics — only the storage backend moved.
- The `/pay` step order. Eight steps, fail-closed at each, same as before.
- `pocketchange/audit.py` — the hash chain is storage-agnostic.

That list is the actual result of the port, and it is the thing worth saying out
loud in the demo: the reasoning layer and the database were both replaced
wholesale, and the part that enforces the limits did not move.

---

## 5. Open

- Bedrock has not been called against real credentials from this machine; the
  offline paths and the test suite are what have been exercised so far.
- Region/model-id pairs need one live check before the demo — see D4.
