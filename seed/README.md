# seed/ — the recall trace

`seed_trace.py` seeds the trace that **Clip 2 (Recall)** retrieves. It POSTs the
Stripe idempotency-fix trace to **production** CommonTrace and then asserts that
a search for the Clip-2 symptom returns that trace **top-1** — which is what makes
the recall clip deterministic.

## Run it once, manually

This is **not** part of the app or the test suite. Run it by hand, one time, when
setting up the demo (and again only if you change the trace content).

```bash
# A FOUNDER CONTRIBUTOR key (founding-door — allowed to contribute). Env only.
export COMMONTRACE_API_KEY=ct_...

python seed/seed_trace.py
```

Stdlib only — no `pip install` needed.

## What it does

1. POSTs the trace *"Stripe webhook double-charges on retried events"* — problem:
   duplicate `charge.succeeded` delivery; solution: idempotency key on
   `event["id"]`; tags `python, fastapi, stripe, webhooks, idempotency`.
2. Polls search for `"duplicate charges on a single order stripe webhook"` (the
   Clip-2 symptom) until the trace is embedded/active and returns **top-1**.
3. Prints the trace id and its `commontrace.org/t/<id>` link.

Submission is asynchronous (the embedding is generated out-of-band), so the trace
is not instantly searchable — the script polls for a while. Tune the wait with
`SEED_POLL_ATTEMPTS` / `SEED_POLL_INTERVAL_S`, and point at a non-prod API with
`COMMONTRACE_API_BASE_URL` if needed.

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | Seeded (or already present) **and** returns top-1 for the Clip-2 query. |
| `1` | Seeded but did not reach top-1 in time — strengthen the content and re-run. |
| `2` | `COMMONTRACE_API_KEY` not set. |
| `3` | Could not reach the API. |

## Secrets

The API key is read from the environment **only**. It is never hardcoded, never
committed, and never logged. `.env` is git-ignored. Contributing requires a
founder / founding-door key; a plain anonymous key will be rejected by the
invitation gate.
