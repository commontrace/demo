"""Stripe webhook charge handling.

A minimal, realistic model of the part of a payments service that reacts to
Stripe `charge.succeeded` webhook events and records what each customer was
charged.

⚠️  KNOWN BUG (this is the demo): `handle_stripe_event` has no idempotency
guard. Stripe delivers webhooks *at least once* — retries and duplicate
deliveries are normal — so a repeated `charge.succeeded` for the same event id
records the charge twice and the customer is billed twice.

`tests/test_payments.py::test_duplicate_event_charges_once` reproduces this and
fails on purpose. The fix is documented in SCRIPT.md and applied on camera.
"""

from __future__ import annotations

from typing import Any


class ChargeStore:
    """In-memory record of charges applied to customers.

    Each recorded charge keeps the originating Stripe ``event_id`` so a handler
    can tell whether an event has already been applied (the basis for an
    idempotency guard).
    """

    def __init__(self) -> None:
        self._charges: list[dict[str, Any]] = []

    def record_charge(self, *, event_id: str, customer: str, amount: int) -> None:
        """Append a charge. Amount is in the smallest currency unit (e.g. cents)."""
        self._charges.append(
            {"event_id": event_id, "customer": customer, "amount": amount}
        )

    def seen_event(self, event_id: str) -> bool:
        """Whether a charge from this Stripe event id has already been recorded."""
        return any(c["event_id"] == event_id for c in self._charges)

    def total_charged(self, customer: str) -> int:
        """Total amount charged to ``customer`` across all recorded charges."""
        return sum(c["amount"] for c in self._charges if c["customer"] == customer)

    @property
    def charge_count(self) -> int:
        """Number of charges recorded (across all customers)."""
        return len(self._charges)


def handle_stripe_event(event: dict, store: ChargeStore) -> None:
    """Apply a single Stripe webhook event to the charge store.

    ``event`` shape::

        {"id": "evt_...", "type": "charge.succeeded",
         "data": {"amount": <int>, "customer": "cus_..."}}

    Only ``charge.succeeded`` events record a charge; everything else is ignored.

    BUG: there is no idempotency check on ``event["id"]`` — a retried or
    duplicated delivery of the same event records the charge again.
    """
    if event.get("type") != "charge.succeeded":
        return

    data = event.get("data") or {}
    store.record_charge(
        event_id=event["id"],
        customer=data["customer"],
        amount=data["amount"],
    )
