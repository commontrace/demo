"""FastAPI wrapper around the payments logic.

This makes the demo read like a real service — Stripe POSTs webhook events to
`/webhooks/stripe` — while the actual charge logic stays in `payments.py` so it
is trivially unit-testable without a running server.

Run locally::

    uvicorn app.api:app --reload

The charge store is a process-local, in-memory singleton — fine for a demo, not
for production.
"""

from __future__ import annotations

from fastapi import FastAPI, Request

from app.payments import ChargeStore, handle_stripe_event

app = FastAPI(title="Payments Service (CommonTrace demo)")

# Process-local store. In a real service this would be a database.
store = ChargeStore()


@app.post("/webhooks/stripe")
async def stripe_webhook(request: Request) -> dict:
    """Receive a Stripe webhook event and apply it to the charge store."""
    event = await request.json()
    handle_stripe_event(event, store)
    return {"received": True}


@app.get("/customers/{customer}/total")
async def customer_total(customer: str) -> dict:
    """Report the total amount charged to a customer (smallest currency unit)."""
    return {"customer": customer, "total_charged": store.total_charged(customer)}


@app.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok", "charges_recorded": store.charge_count}
