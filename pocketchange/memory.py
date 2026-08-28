"""What survives between sessions.

Everything else in this system is per-run. A mandate is signed, spent and
finished inside one process, and when the process exits nothing remembers it
happened. That is fine for an errand and useless for a standing instruction:
"keep the stationery cupboard stocked" only means something if the system knows
what it bought last week and how much of this quarter's budget is left.

This is the gap the enterprise brief calls "context across weeks of asynchronous
operation", and it is the one row that project failed.

Two things are remembered, and only two:

  the instruction   what a person said once, and the reorder policy derived
                    from it, so a later tick does not re-interpret the sentence
  the spend         how much of the period budget has gone, so the ledger's
                    per-mandate ceiling is not silently reset every time a new
                    mandate is minted

The second is the subtle one. Each tick mints a fresh mandate; without a
remembered period total, a standing order would get a full budget every tick and
the cap would mean nothing.
"""

from __future__ import annotations

import os
import threading
import uuid
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from typing import Protocol

PERIODS = {"week": timedelta(days=7), "month": timedelta(days=30),
           "quarter": timedelta(days=91)}


class MemoryError_(Exception):
    """Base for everything this module refuses."""


class UnknownOrder(MemoryError_):
    """No standing order under that id."""


@dataclass(frozen=True)
class ReorderRule:
    """One line of the policy a standing instruction implies."""

    sku: str
    reorder_point: int
    target_level: int

    def as_dict(self) -> dict:
        return {"sku": self.sku, "reorder_point": self.reorder_point,
                "target_level": self.target_level}


@dataclass(frozen=True)
class StandingOrder:
    """A person's instruction, plus everything needed to act on it later."""

    id: str
    instruction: str                 # their original words, kept verbatim
    department: str
    period: str                      # week | month | quarter
    period_budget_paise: int
    rules: tuple[ReorderRule, ...]
    created_at: datetime
    period_started_at: datetime
    spent_this_period_paise: int = 0
    last_checked_at: datetime | None = None
    checks: int = 0
    # Inert until a person authorises it. A standing order creates RECURRING
    # authority from a single sentence, and does so in the one mode where
    # nobody is watching - so it is the place an approval is most warranted,
    # not least.
    approved: bool = False
    active: bool = True
    notes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def remaining_paise(self) -> int:
        return max(0, self.period_budget_paise - self.spent_this_period_paise)

    def period_expired(self, now: datetime | None = None) -> bool:
        now = now or datetime.now(timezone.utc)
        return now - self.period_started_at >= PERIODS[self.period]

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "instruction": self.instruction,
            "department": self.department,
            "period": self.period,
            "period_budget_paise": self.period_budget_paise,
            "spent_this_period_paise": self.spent_this_period_paise,
            "remaining_paise": self.remaining_paise,
            "rules": [rule.as_dict() for rule in self.rules],
            "created_at": self.created_at.isoformat(),
            "period_started_at": self.period_started_at.isoformat(),
            "last_checked_at": self.last_checked_at.isoformat() if self.last_checked_at else None,
            "checks": self.checks,
            "approved": self.approved,
            "active": self.active,
            "notes": list(self.notes),
        }


class MemoryBank(Protocol):
    """What the standing branch needs to survive a restart."""

    def remember(self, order: StandingOrder) -> StandingOrder: ...
    def recall(self, order_id: str) -> StandingOrder: ...
    def standing_orders(self, department: str | None = None, *,
                        include_pending: bool = False) -> list[StandingOrder]: ...
    def record_check(self, order_id: str, *, spent_paise: int, note: str) -> StandingOrder: ...


class InMemoryBank:
    """Correct, not durable. Used in tests and when no project is configured."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._orders: dict[str, StandingOrder] = {}

    def remember(self, order: StandingOrder) -> StandingOrder:
        with self._lock:
            self._orders[order.id] = order
            return order

    def recall(self, order_id: str) -> StandingOrder:
        with self._lock:
            if order_id not in self._orders:
                raise UnknownOrder(f"no standing order {order_id}")
            return self._orders[order_id]

    def approve(self, order_id: str, *, by: str = "human") -> StandingOrder:
        """Authorise a policy to start running."""
        with self._lock:
            order = self._orders.get(order_id)
            if order is None:
                raise UnknownOrder(f"no standing order {order_id}")
            order = replace(order, approved=True,
                            notes=(order.notes + (f"approved by {by}",))[-20:])
            self._orders[order_id] = order
            return order

    def standing_orders(self, department: str | None = None, *,
                        include_pending: bool = False) -> list[StandingOrder]:
        """Approved and active orders - the ones that may actually run.

        `include_pending` adds drafted-but-unapproved ones. Not for the tick
        loop, which must only ever see policies a person authorised, but the
        console needs them: "inert until approved" is the entire security story
        here, and a policy waiting for a human was invisible to every reader.
        """
        with self._lock:
            return sorted(
                (o for o in self._orders.values()
                 if o.active and (o.approved or include_pending)
                 and (department is None or o.department == department)),
                key=lambda o: o.created_at,
            )

    def record_check(self, order_id: str, *, spent_paise: int, note: str) -> StandingOrder:
        """Note that a tick happened, and what it cost.

        Rolls the period first if it has elapsed, so a quarter's budget resets
        exactly once rather than drifting with whenever someone happened to run.
        """
        now = datetime.now(timezone.utc)
        with self._lock:
            order = self._orders.get(order_id)
            if order is None:
                raise UnknownOrder(f"no standing order {order_id}")

            if order.period_expired(now):
                order = replace(order, period_started_at=now, spent_this_period_paise=0)

            if spent_paise > order.remaining_paise:
                raise MemoryError_(
                    f"{order_id} has {order.remaining_paise}p left this "
                    f"{order.period}, tried to spend {spent_paise}p"
                )

            order = replace(
                order,
                spent_this_period_paise=order.spent_this_period_paise + spent_paise,
                last_checked_at=now,
                checks=order.checks + 1,
                notes=(order.notes + (note,))[-20:],
            )
            self._orders[order_id] = order
            return order

    def deactivate(self, order_id: str) -> StandingOrder:
        with self._lock:
            order = self._orders[order_id]
            order = replace(order, active=False)
            self._orders[order_id] = order
            return order

    def __len__(self) -> int:
        with self._lock:
            return len(self._orders)


def new_order(
    *, instruction: str, department: str, period: str, period_budget_paise: int,
    rules: tuple[ReorderRule, ...],
) -> StandingOrder:
    if period not in PERIODS:
        raise ValueError(f"unknown period {period!r}; use one of {sorted(PERIODS)}")
    now = datetime.now(timezone.utc)
    return StandingOrder(
        id=f"so_{uuid.uuid4().hex[:10]}",
        instruction=instruction, department=department, period=period,
        period_budget_paise=period_budget_paise, rules=rules,
        created_at=now, period_started_at=now,
    )


def from_env() -> MemoryBank:
    """Firestore when a project is configured, in-memory otherwise.

    Same rule as the ledger: development and tests must never need credentials,
    so absence degrades rather than fails.
    """
    if not os.getenv("GOOGLE_CLOUD_PROJECT", "").strip():
        return InMemoryBank()
    try:
        from .memory_firestore import FirestoreBank

        return FirestoreBank()
    except Exception:  # noqa: BLE001 - unreachable storage must not stop local work
        return InMemoryBank()
