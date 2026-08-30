"""Exercise the real Firestore ledger: the same invariants, durable storage.

Run:  .venv/bin/python scripts/smoke_firestore.py
Needs ADC and a Firestore database.
"""

import uuid

from pocketchange import config
from pocketchange.ledger import FirestoreLedger, InsufficientBudget
from pocketchange.policy import RUPEE

config.load()

import os  # noqa: E402

ledger = FirestoreLedger(project=os.environ["GOOGLE_CLOUD_PROJECT"])
mandate = f"smoke-{uuid.uuid4().hex[:12]}"
ok = 0


def check(label: str, condition: bool) -> None:
    global ok
    ok += bool(condition)
    print(f"  [{'PASS' if condition else 'FAIL'}] {label}")


print(f"\nmandate {mandate}\n")

s = ledger.open(mandate, 600_000 * RUPEE)
check("opened with a 1500 rupee cap", s.cap_paise == 600_000 * RUPEE)

first = ledger.reserve(mandate, 359_600 * RUPEE, "cart-a")
check("reserve holds budget before any charge",
      ledger.state(mandate).reserved_paise == 359_600 * RUPEE)

again = ledger.reserve(mandate, 359_600 * RUPEE, "cart-a")
check("same key returns the same reservation", again.id == first.id)
check("and does not double-hold", ledger.state(mandate).reserved_paise == 359_600 * RUPEE)

s = ledger.commit(first.id)
check("commit turns the hold into spend",
      s.committed_paise == 359_600 * RUPEE and s.reserved_paise == 0)

try:
    ledger.reserve(mandate, 359_600 * RUPEE, "cart-b")
    check("cumulative spend refuses the second payment", False)
except InsufficientBudget as exc:
    check("cumulative spend refuses the second payment", exc.available == 240_400 * RUPEE)

held = ledger.reserve(mandate, 200_000 * RUPEE, "cart-c")
ledger.release(held.id)
s = ledger.state(mandate)
check("release returns the budget", s.reserved_paise == 0 and s.available_paise == 240_400 * RUPEE)

retry = ledger.reserve(mandate, 200_000 * RUPEE, "cart-c")
check("a released key is retryable", retry.id != held.id)
ledger.release(retry.id)

TOTAL = 8
print(f"\n{ok}/{TOTAL} gates passed")
print("durable: this mandate is now a real document in Firestore.\n")
raise SystemExit(0 if ok == TOTAL else 1)
