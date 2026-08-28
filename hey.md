# hey

Our working canvas. Diagrams first, prose only where a diagram cannot say it.

---

## 1. The orchestra, as LangGraph

Pocket Change's buyer, expressed the way RabbitHole expresses its courtroom.
This is the *design*, not what is currently built — see §6.

```
                                START
                                  │
                                  ▼
                        ┌───────────────────┐
                        │   intake_node     │  parse the request
                        └─────────┬─────────┘  bind mandate + tokens
                                  │
                                  ▼
              ┌──────────────────────────────────────┐
              │        constraint_node               │◄─────────────┐
              │  round n · what budget is left       │              │
              │  what the last refusal said          │              │
              └──────────────────┬───────────────────┘              │
                                 │                                  │
                    add_conditional_edges                           │
                    route_to_active_shoppers                        │
                                 │                                  │
          ┌──────────────┬───────┴───────┬──────────────┐           │
          ▼              ▼               ▼              ▼           │
    ┌───────────┐  ┌───────────┐  ┌───────────┐   (only the         │
    │  thrifty  │  │ complete  │  │ balanced  │    strategies       │
    │  shopper  │  │  shopper  │  │  shopper  │    worth running    │
    └─────┬─────┘  └─────┬─────┘  └─────┬─────┘    this round)      │
          │              │              │                          │
          └──────────────┴───────┬──────┘                          │
                                 │                                 │
                    proposals: Annotated[dict, merge_proposals]     │
                    ── the reducer. three writers, no clobbering ── │
                                 │                                 │
                                 ▼                                 │
                        ┌───────────────────┐                      │
                        │   chooser_node    │  one cart wins       │
                        │   names the       │  and the trade-off   │
                        │   trade-off       │  is stated           │
                        └─────────┬─────────┘                      │
                                  │                                │
                                  ▼                                │
                        ┌───────────────────┐                      │
                        │    payer_node     │  ──► GATEWAY         │
                        │  never saw a      │      (9 checks,      │
                        │  listing          │       external)      │
                        └─────────┬─────────┘                      │
                                  │                                │
                                  ▼                                │
                        ┌───────────────────┐                      │
                        │   outcome_node    │  classify the        │
                        │                   │  refusal            │
                        └─────────┬─────────┘                      │
                                  │                                │
                    add_conditional_edges                          │
                    route_after_outcome                            │
                                  │                                │
      ┌──────────┬────────────────┼────────────────┬───────────┐   │
      │          │                │                │           │   │
   "done"    "continue"       "give_up"        "waiting"        │   │
      │          │                │                │           │   │
      │          └────────────────┼────────────────┼───────────┼───┘
      │                           │                │           │
      │                           │                ▼           │
      │                           │      ┌───────────────────┐ │
      │                           │      │    hitl_node      │ │
      │                           │      │ interrupt_before  │ │
      │                           │      │ graph SUSPENDS    │ │
      │                           │      │ checkpointer      │ │
      │                           │      │ holds the         │ │
      │                           │      │ reservation       │ │
      │                           │      └─────────┬─────────┘ │
      │                           │                │           │
      │                           │      add_conditional_edges │
      │                           │      route_after_hitl      │
      │                           │                │           │
      │                           │      ┌─────────┴────────┐  │
      │                           │   approved           denied│
      │                           │      │                  │  │
      │                           │      └──► payer_node    │  │
      │                           │                         │  │
      ▼                           ▼                         ▼  │
   ┌────────────────────────────────────────────────────────────┐
   │                    conclusion_node                          │
   │        what was bought, what was refused, why               │
   └──────────────────────────┬─────────────────────────────────┘
                              ▼
                             END
```

---

## 2. Nodes

| node | reads | writes | trust |
|---|---|---|---|
| `intake_node` | user request | `request`, tokens | trusted setup |
| `constraint_node` | `last_refusal`, `remaining_paise` | `iteration`, clears `proposals` | trusted |
| `shopper_*` ×3 | **seller-controlled listings** | one `proposals[strategy]` | **untrusted · no pay** |
| `chooser_node` | `proposals`, budget | `cart`, `chosen_strategy` | untrusted · no listings |
| `payer_node` | `cart` | `last_refusal` or order id | **untrusted · pay only** |
| `outcome_node` | `last_refusal` | `next_action` | trusted, pure code |
| `hitl_node` | pending approval | human decision | **human** |
| `conclusion_node` | everything | `outcome` | trusted |

---

## 3. State

```
ErrandState(TypedDict)
├── request              str
├── iteration            int
├── proposals            Annotated[dict[str, Proposal], merge_proposals]   ◄── reducer
├── chosen_strategy      str
├── choice_reason        str
├── cart                 dict[sku, qty]
├── last_refusal         RefusalState | None
│     ├── reason         str
│     ├── available      int      ◄── what makes re-planning possible
│     ├── cap            int
│     └── committed      int
├── remaining_paise      int | None
├── pending_approval     str | None                                        ◄── HITL
├── history              list[str]
├── next_action          Literal["done","continue","give_up","waiting"]
└── outcome              str
```

The reducer is the only field that needs one, and it needs one because three
shoppers write `proposals` at the same time. Everything else has a single writer.

---

## 4. The two conditional edges

```
route_after_outcome(state)                    route_after_hitl(state)
──────────────────────────                    ───────────────────────
  no refusal          → conclusion              approved → payer_node
  budget, room left   → constraint_node ⟲       denied   → conclusion
  budget, no room     → conclusion              timeout  → conclusion
  scope refused       → conclusion   (never retried — attenuation
                                      only narrows, so authority the
                                      chain never held cannot appear)
  escalated           → hitl_node
  round == max        → conclusion
```

Both are **plain functions over state**, not prompts. A rule that lives only
inside a prompt cannot be asserted on, and a model that feels optimistic will
retry a scope refusal forever.

---

## 5. Where RAG would attach

```
constraint_node ──► catalog_rag_node ──► shoppers
                    │
                    └── retrieve · grade · self-correct
                        (RabbitHole's rag/structure, same shape)
```

Not drawn in detail yet. Flagged so §1 does not have to be redrawn later.

---

## 6. What is actually built today

Same topology, expressed in ADK rather than LangGraph:

```
LangGraph (this design)          ADK (built, 61 tests green)
────────────────────────         ───────────────────────────
StateGraph + edges          →    LoopAgent / ParallelAgent nesting
constraint_node             →    tools.current_constraint()
Annotated[..., reducer]     →    graph/reducers.py + round_open guard
add_conditional_edges       →    graph/route.py  (built, tested)
interrupt_before + saver    →    NOT BUILT  ◄── the real gap
checkpointer                →    NOT BUILT
intake / conclusion nodes   →    NOT BUILT  (script does it)
catalog_rag_node            →    NOT BUILT
```

The gap that matters is `hitl_node`. Today an escalation returns HTTP 409 and
the run dies — a refusal wearing the word "escalate".

---

## 7. Open, for you

1. **LangGraph or ADK?** ATA requires a *Google* agent framework. LangGraph is the
   better fit for this shape and is what you already know; it may cost the ATA
   entry. ADK can express all of it except cleanly checkpointed interrupts.
2. **`intake` and `conclusion`** — real nodes, or leave that to the caller?
3. **Do all three shoppers always run?** `route_to_active_shoppers` is drawn as
   conditional, mirroring your moderator. Worth it, or always-three?
