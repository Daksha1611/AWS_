"""Who we have actually paid, and how often.

The one reputation signal a seller cannot write.

Everything the buyer currently knows about a counterparty comes from the
counterparty. `merchant/sellers.py` computes `is_established` from
`trading_months >= 12 and review_count >= 100`, and both numbers sit in the
seller's own record; `agent/tools.py:seller_reputation` hands them to the
shopper. A hostile supplier sets review_count to a hundred thousand and is
"established" for free. That is the Sybil shape SoK calls Identity-to-Market,
and it is why `eval/vectors.py` had it marked not applicable - we had no
counter-evidence to offer.

This is the counter-evidence. It is written by the GATEWAY at settlement, from
payments that actually cleared, so it cannot be inflated by anyone outside this
process. A supplier can claim anything about itself; it cannot make us have paid
it before.

Be precise about what is and is not trusted:

  the IDENTITY  is declared on the payment by the agent, and the agent is the
                component we assume is compromised. It can misattribute.
  the HISTORY   is ours. Orders, totals and first-seen dates come from our own
                settled payments, and no amount of seller-side fabrication
                touches them.

So this does not answer "is this supplier honest". It answers "have we, in fact,
dealt with whoever this payment says it is dealing with" - which is exactly the
question the review-count signal cannot be trusted to answer.
"""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Protocol


@dataclass(frozen=True)
class Counterparty:
    """Our own record of dealings with one party."""

    id: str
    first_paid: datetime
    last_paid: datetime
    orders: int
    total_paise: int
    mandates: int          # distinct mandates that have paid them

    # --- how it went ---------------------------------------------------------
    #
    # An order count on its own is not a reputation, it is a tally, and a tally
    # is exactly what a bad counterparty wants you reading. Forty settled orders
    # alongside five escalations and two human refusals is a WORSE record than no
    # history at all, and a summary that reports only the forty reproduces the
    # sybil problem one level up - the thing this module exists to fix.
    escalated: int = 0     # the monitor stopped a payment to them for a person
    refused: int = 0       # the gateway denied a payment naming them
    vetoed: int = 0        # a HUMAN looked and said no. the strongest signal here
    injections: int = 0    # pages attributed to them carried instruction-shaped text

    @property
    def trouble(self) -> int:
        """Everything that went wrong, however it went wrong."""
        return self.escalated + self.refused + self.vetoed + self.injections

    @property
    def only_once(self) -> bool:
        """Exactly one prior dealing. Thin history, but not no history.

        Note what this is NOT: "this is their first payment". A record only
        exists once something has cleared, so the never-dealt-with case is the
        ABSENCE of a row - see NEW - not a row with one order in it. Conflating
        the two made a supplier we had already paid keep reading as unknown.
        """
        return self.orders == 1

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "first_paid": self.first_paid.isoformat(),
            "last_paid": self.last_paid.isoformat(),
            "orders": self.orders,
            "total_paise": self.total_paise,
            "mandates": self.mandates,
            "only_once": self.only_once,
            "escalated": self.escalated,
            "refused": self.refused,
            "vetoed": self.vetoed,
            "injections": self.injections,
            "trouble": self.trouble,
        }

    def describe(self) -> str:
        """One line for the monitor, describing the record as it already stands.

        Trouble comes FIRST, and deliberately. A model reading "paid 40 times,
        12,00,000 rupees" and then, eventually, "2 refused by a person" will
        anchor on the forty. The reverse ordering costs nothing and stops a long
        tally being used as cover.

        Never says "never": a Counterparty only exists because a payment cleared,
        so absence of a record is the no-history case, reported by the caller.
        """
        rupees = f"{self.total_paise // 100:,} rupees"
        days = max(0, (self.last_paid - self.first_paid).days)
        span = f" over {days} days" if days else ""
        if self.orders == 0:
            settled = "never paid"
        elif self.orders == 1:
            settled = f"paid once before, {rupees}"
        else:
            settled = f"paid {self.orders} times{span}, {rupees} in total"

        if not self.trouble:
            return settled

        bad = []
        if self.vetoed:
            bad.append(f"{self.vetoed} refused by a person")
        if self.injections:
            bad.append(f"{self.injections} page(s) from them carried injected instructions")
        if self.escalated:
            bad.append(f"{self.escalated} held for review")
        if self.refused:
            bad.append(f"{self.refused} refused by the gateway")
        return f"CONCERNS: {'; '.join(bad)} - and {settled}"


UNKNOWN = "not stated"
NEW = "never paid before"


# What can go wrong, and be remembered.
ESCALATED = "escalated"   # the monitor stopped a payment for a person
REFUSED = "refused"       # the gateway denied a payment naming them
VETOED = "vetoed"         # a person looked and said no
INJECTION = "injections"  # a page attributed to them carried instructions
FLAGS = (ESCALATED, REFUSED, VETOED, INJECTION)


class CounterpartyBook(Protocol):
    def record(self, counterparty: str, *, amount_paise: int, mandate_id: str) -> Counterparty: ...
    def flag(self, counterparty: str, kind: str) -> Counterparty: ...
    def lookup(self, counterparty: str) -> Counterparty | None: ...
    def all(self) -> list[Counterparty]: ...


class InMemoryCounterparties:
    """Process-local. Loses history on restart, which is honest about what it is."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._rows: dict[str, Counterparty] = {}
        self._mandates: dict[str, set[str]] = {}

    def record(self, counterparty: str, *, amount_paise: int, mandate_id: str) -> Counterparty:
        key = counterparty.strip()
        if not key:
            raise ValueError("a counterparty needs an identifier to be remembered")
        now = datetime.now(timezone.utc)
        with self._lock:
            seen = self._mandates.setdefault(key, set())
            seen.add(mandate_id)
            prior = self._rows.get(key)
            # replace(), not a fresh construction: building a new Counterparty
            # here silently dropped every flag, so a party we had refused or
            # caught injecting became clean again the moment they were paid -
            # rewarding exactly the behaviour the flags exist to remember.
            base = prior or Counterparty(key, now, now, 0, 0, 0)
            row = replace(
                base,
                first_paid=prior.first_paid if prior else now,
                last_paid=now,
                orders=base.orders + 1,
                total_paise=base.total_paise + amount_paise,
                mandates=len(seen),
            )
            self._rows[key] = row
            return row

    def flag(self, counterparty: str, kind: str) -> Counterparty:
        """Remember that something went wrong with this party.

        A flag needs no settled payment behind it - that is the point. A supplier
        whose pages carry injected instructions, or whose payment a person
        refused, has a record with us even though we never paid them, and that
        record is worth more than the absence of one.
        """
        key = counterparty.strip()
        if not key:
            raise ValueError("a counterparty needs an identifier to be flagged")
        if kind not in FLAGS:
            raise ValueError(f"unknown flag {kind!r}; expected one of {FLAGS}")
        now = datetime.now(timezone.utc)
        with self._lock:
            prior = self._rows.get(key)
            base = prior or Counterparty(key, now, now, 0, 0, 0)
            row = replace(base, **{kind: getattr(base, kind) + 1})
            self._rows[key] = row
            return row

    def lookup(self, counterparty: str) -> Counterparty | None:
        return self._rows.get(counterparty.strip())

    def all(self) -> list[Counterparty]:
        with self._lock:
            return sorted(self._rows.values(), key=lambda c: -c.orders)

    def __len__(self) -> int:
        return len(self._rows)


class FirestoreCounterparties:
    """Durable, so the record survives a restart and spans deployments.

    Layout:
        counterparties/{id}   first_paid, last_paid, orders, total_paise, mandates[]

    A transaction per settlement, matching FirestoreLedger. The list of mandate
    ids is kept rather than a count so the figure stays correct when the same
    mandate pays a supplier twice.
    """

    def __init__(self, project: str | None = None, prefix: str = "counterparties") -> None:
        from google.cloud import firestore

        self._firestore = firestore
        self._db = firestore.Client(project=project) if project else firestore.Client()
        self._prefix = prefix

    def _ref(self, counterparty: str):
        return self._db.collection(self._prefix).document(counterparty)

    def record(self, counterparty: str, *, amount_paise: int, mandate_id: str) -> Counterparty:
        key = counterparty.strip()
        if not key:
            raise ValueError("a counterparty needs an identifier to be remembered")
        ref = self._ref(key)
        now = datetime.now(timezone.utc)

        @self._firestore.transactional
        def apply(txn):
            snap = ref.get(transaction=txn)
            data = snap.to_dict() if snap.exists else {}
            mandates = set(data.get("mandates", []))
            mandates.add(mandate_id)
            row = {
                "first_paid": data.get("first_paid", now),
                "last_paid": now,
                "orders": int(data.get("orders", 0)) + 1,
                "total_paise": int(data.get("total_paise", 0)) + amount_paise,
                "mandates": sorted(mandates),
            }
            txn.set(ref, row)
            return row

        row = apply(self._db.transaction())
        return _row_to_counterparty(key, row)

    def flag(self, counterparty: str, kind: str) -> Counterparty:
        key = counterparty.strip()
        if not key:
            raise ValueError("a counterparty needs an identifier to be flagged")
        if kind not in FLAGS:
            raise ValueError(f"unknown flag {kind!r}; expected one of {FLAGS}")
        ref = self._ref(key)
        now = datetime.now(timezone.utc)

        @self._firestore.transactional
        def apply(txn):
            snap = ref.get(transaction=txn)
            data = dict(snap.to_dict()) if snap.exists else {}
            data.setdefault("first_paid", now)
            data.setdefault("last_paid", now)
            data[kind] = int(data.get(kind, 0)) + 1
            txn.set(ref, data)
            return data

        return _row_to_counterparty(key, apply(self._db.transaction()))

    def lookup(self, counterparty: str) -> Counterparty | None:
        snap = self._ref(counterparty.strip()).get()
        if not snap.exists:
            return None
        return _row_to_counterparty(counterparty.strip(), snap.to_dict())

    def all(self) -> list[Counterparty]:
        rows = [_row_to_counterparty(d.id, d.to_dict())
                for d in self._db.collection(self._prefix).stream()]
        return sorted(rows, key=lambda c: -c.orders)


def _as_datetime(value) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc)


def _row_to_counterparty(key: str, row: dict) -> Counterparty:
    return Counterparty(
        id=key,
        first_paid=_as_datetime(row.get("first_paid")),
        last_paid=_as_datetime(row.get("last_paid")),
        orders=int(row.get("orders", 0)),
        total_paise=int(row.get("total_paise", 0)),
        mandates=len(row.get("mandates", []) or []),
        escalated=int(row.get("escalated", 0)),
        refused=int(row.get("refused", 0)),
        vetoed=int(row.get("vetoed", 0)),
        injections=int(row.get("injections", 0)),
    )


def from_env() -> CounterpartyBook:
    """Firestore when a project is configured, in-memory otherwise.

    Same degradation as the ledger: local work and tests must never need cloud
    credentials, and an unreachable Firestore must not stop a payment.
    """
    project = os.getenv("GOOGLE_CLOUD_PROJECT", "").strip()
    if not project:
        return InMemoryCounterparties()
    try:
        return FirestoreCounterparties(project=project)
    except Exception:  # noqa: BLE001
        return InMemoryCounterparties()
