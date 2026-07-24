# Plan

Two small tasks. Work them in order.

## Task 1 — Some customers say they were charged twice; find and fix it

Support is getting reports: a handful of customers were billed twice for a
single order. The payments service applies Stripe `charge.succeeded` webhooks in
`app/payments.py`.

- Reproduce the double-charge (there's a failing test in `tests/test_payments.py`).
- Find the root cause in `handle_stripe_event`.
- Fix it so a retried or duplicated delivery of the same event only charges once.
- Get the whole test suite green.

Acceptance: `python -m pytest -q` passes, including
`test_duplicate_event_charges_once`.

## Task 2 — Send an order-confirmation email

After a charge succeeds, send the customer a short order-confirmation email.

- Add a tiny `send_order_confirmation(customer, amount)` helper (stub the actual
  transport — a `print(...)` / logger call is fine for the demo).
- Call it from the charge path once, after the charge is recorded.

Acceptance: a confirmation is emitted exactly once per successful charge.
