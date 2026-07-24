"""Tiny payments service used by the CommonTrace demo.

Ships with a deliberate double-charge bug in `payments.handle_stripe_event`
(no idempotency guard on the Stripe event id). See README.md and SCRIPT.md.
"""

from app.payments import ChargeStore, handle_stripe_event

__all__ = ["ChargeStore", "handle_stripe_event"]
