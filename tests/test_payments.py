"""Tests for the Stripe webhook charge handling.

`test_duplicate_event_charges_once` is the star of the demo: it reproduces the
double-charge and **fails on `main`** because `handle_stripe_event` has no
idempotency guard. The on-camera fix (a one-line guard on `event["id"]`) makes
it pass. Every other test in this file passes in both states.

These are `unittest.TestCase` methods rather than bare pytest functions so the
demo runs with **zero installed dependencies**: `python3 -m unittest -q` works
on any stock Python 3.10+, including the Debian/Ubuntu boxes where PEP 668
refuses a bare `pip install`. pytest collects TestCase subclasses too, so
`python3 -m pytest -q` still gives the nicer on-camera output — and still
rewrites the bare asserts below into a readable `8400 == 4200` diff — whenever
pytest happens to be installed.
"""

import unittest

from app.payments import ChargeStore, handle_stripe_event


def _charge_event(event_id: str, customer: str, amount: int) -> dict:
    return {
        "id": event_id,
        "type": "charge.succeeded",
        "data": {"amount": amount, "customer": customer},
    }


class TestCharges(unittest.TestCase):
    def test_single_charge_records_amount(self):
        store = ChargeStore()
        handle_stripe_event(_charge_event("evt_1", "cus_9", 4200), store)
        assert store.total_charged("cus_9") == 4200

    def test_duplicate_event_charges_once(self):
        """A retried / duplicated Stripe delivery must not double-charge.

        Stripe delivers webhooks at least once, so the same event id can arrive
        more than once. FAILS on `main`: the customer is charged 8400 instead of
        4200. Fixing this (idempotency key on event["id"]) is the demo.
        """
        store = ChargeStore()
        evt = _charge_event("evt_1", "cus_9", 4200)
        handle_stripe_event(evt, store)
        handle_stripe_event(evt, store)  # Stripe retry / duplicate delivery
        assert store.total_charged("cus_9") == 4200

    def test_distinct_events_accumulate(self):
        """Two *different* events for the same customer are two real charges."""
        store = ChargeStore()
        handle_stripe_event(_charge_event("evt_1", "cus_9", 4200), store)
        handle_stripe_event(_charge_event("evt_2", "cus_9", 1500), store)
        assert store.total_charged("cus_9") == 5700

    def test_non_charge_events_ignored(self):
        """Only charge.succeeded records money; other event types are ignored."""
        store = ChargeStore()
        handle_stripe_event(
            {"id": "evt_x", "type": "payment_intent.created", "data": {}}, store
        )
        assert store.total_charged("cus_9") == 0
        assert store.charge_count == 0

    def test_charges_are_isolated_per_customer(self):
        store = ChargeStore()
        handle_stripe_event(_charge_event("evt_1", "cus_a", 1000), store)
        handle_stripe_event(_charge_event("evt_2", "cus_b", 2000), store)
        assert store.total_charged("cus_a") == 1000
        assert store.total_charged("cus_b") == 2000


if __name__ == "__main__":
    unittest.main()
