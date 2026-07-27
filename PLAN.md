# Plan

## Task 1: Some customers say they were charged twice; find and fix it

Support is getting reports: a handful of customers were billed twice for a
single order. The payments service applies Stripe `charge.succeeded` webhooks in
`app/payments.py`.

- Reproduce the double-charge (there's a failing test in `tests/test_payments.py`).
- Find the root cause in `handle_stripe_event`.
- Fix it so a retried or duplicated delivery of the same event only charges once.
- Get the whole test suite green.

Acceptance: `python -m pytest -q` passes, including
`test_duplicate_event_charges_once`.
