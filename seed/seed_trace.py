#!/usr/bin/env python3
"""Seed the recall trace for the CommonTrace demo (Clip 2).

POSTs the Stripe idempotency-fix trace to **production** CommonTrace, then polls
search for the Clip-2 symptom and asserts the seeded trace comes back **top-1**.
This is what makes the recall clip deterministic: a fresh agent hitting the same
double-charge retrieves this trace first, every time.

Run manually, once, with the key the trace should be attributed to:

    export COMMONTRACE_API_KEY=ct_...        # any registered key can publish
    python seed/seed_trace.py

Exit codes:
    0  trace seeded (or already searchable) AND returns top-1 for the Clip-2 query
    1  seeded but did not reach top-1 within the timeout (tune content and re-run)
    2  configuration error (missing API key)
    3  HTTP / transport error talking to the API

The API key is read from the environment only — it is NEVER hardcoded or logged.
Uses the Python standard library only (no pip install needed).
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE_URL = os.environ.get("COMMONTRACE_API_BASE_URL", "https://api.commontrace.org").rstrip("/")
API_KEY = os.environ.get("COMMONTRACE_API_KEY", "").strip()

# The verbatim Clip-2 symptom the recording agent describes. The seeded trace
# must return TOP-1 for this query.
CLIP2_QUERY = "duplicate charges on a single order stripe webhook"

# How long to wait for async embedding/activation to make the trace searchable.
POLL_ATTEMPTS = int(os.environ.get("SEED_POLL_ATTEMPTS", "40"))
POLL_INTERVAL_S = float(os.environ.get("SEED_POLL_INTERVAL_S", "6"))

TRACE = {
    "title": "Stripe webhook double-charges on retried events",
    "context_text": (
        "A Python/FastAPI payments service records a charge every time it "
        "receives a Stripe `charge.succeeded` webhook event. Some customers "
        "report being charged twice for a single order. Stripe delivers "
        "webhooks *at least once* — it retries on any non-2xx or timeout and can "
        "deliver the same event more than once — so the handler processes the "
        "same `charge.succeeded` event id repeatedly and applies the charge "
        "twice. The webhook handler has no idempotency guard: it does not track "
        "which Stripe event ids it has already processed, so duplicate and "
        "retried deliveries silently double-charge."
    ),
    "solution_text": (
        "Make the webhook handler idempotent by keying on the Stripe event id "
        "(`event[\"id\"]`, e.g. `evt_...`), which is stable across retries and "
        "duplicate deliveries. Before applying any side effect (recording the "
        "charge, sending email), check whether that event id has already been "
        "processed; if so, return early and still respond 200 so Stripe stops "
        "retrying.\n\n"
        "    def handle_stripe_event(event, store):\n"
        "        if event.get(\"type\") != \"charge.succeeded\":\n"
        "            return\n"
        "        if store.seen_event(event[\"id\"]):   # idempotency guard\n"
        "            return                            # duplicate/retried delivery\n"
        "        data = event.get(\"data\") or {}\n"
        "        store.record_charge(\n"
        "            event_id=event[\"id\"],\n"
        "            customer=data[\"customer\"],\n"
        "            amount=data[\"amount\"],\n"
        "        )\n\n"
        "In a real service, persist processed event ids (a unique column / "
        "processed-events table with a UNIQUE constraint on the event id, or a "
        "Redis SET) so idempotency survives restarts and concurrent deliveries; "
        "an INSERT that violates the unique constraint means 'already handled'. "
        "Add a regression test that delivers the same event twice and asserts a "
        "single charge."
    ),
    "tags": ["python", "fastapi", "stripe", "webhooks", "idempotency"],
    "agent_model": "claude-opus-4-8",
    "metadata_json": {
        "detection_pattern": "error_resolution",
        "error_count": 3,
        "time_to_resolution_minutes": 25,
        "iteration_count": 2,
        "language": "python",
        "framework": "fastapi",
    },
    "tokens_to_resolution": 400000,
}


def _post(path: str, payload: dict) -> tuple[int, dict]:
    """POST JSON with the API key header. Returns (status_code, parsed_body)."""
    url = f"{BASE_URL}{path}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("X-API-Key", API_KEY)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, (json.loads(body) if body else {})
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        try:
            parsed = json.loads(body)
        except ValueError:
            parsed = {"raw": body}
        return e.code, parsed


def main() -> int:
    if not API_KEY:
        print("ERROR: COMMONTRACE_API_KEY is not set. Export a founder contributor "
              "key and re-run. The key is read from the environment only.",
              file=sys.stderr)
        return 2

    print(f"Seeding recall trace to {BASE_URL} ...")
    try:
        status, body = _post("/api/v1/traces", TRACE)
    except urllib.error.URLError as e:
        print(f"ERROR: could not reach the API: {e}", file=sys.stderr)
        return 3

    if status not in (200, 201, 202):
        print(f"ERROR: trace submission failed (HTTP {status}): {body}", file=sys.stderr)
        return 1

    trace_id = str(body.get("id", "")).strip()
    if not trace_id:
        print(f"ERROR: submission accepted but no trace id returned: {body}", file=sys.stderr)
        return 1
    print(f"Submitted. trace id = {trace_id} (status: {body.get('status', 'pending')})")

    # Poll search until the trace is embedded/active and returns top-1. Submission
    # is async — the embedding is generated out-of-band, so the trace is not
    # instantly searchable.
    print(f'Waiting for it to become searchable and top-1 for: "{CLIP2_QUERY}"')
    best_rank = None
    for attempt in range(1, POLL_ATTEMPTS + 1):
        try:
            s_status, s_body = _post(
                "/api/v1/traces/search", {"q": CLIP2_QUERY, "limit": 5}
            )
        except urllib.error.URLError as e:
            print(f"  attempt {attempt}: search transport error: {e}")
            time.sleep(POLL_INTERVAL_S)
            continue

        if s_status != 200:
            print(f"  attempt {attempt}: search HTTP {s_status}: {s_body}")
            time.sleep(POLL_INTERVAL_S)
            continue

        results = s_body.get("results", []) if isinstance(s_body, dict) else []
        ids = [str(r.get("id", "")) for r in results]
        if trace_id in ids:
            rank = ids.index(trace_id) + 1  # 1-based
            best_rank = rank if best_rank is None else min(best_rank, rank)
            top = results[0]
            print(f"  attempt {attempt}: found at rank {rank}/{len(ids)} "
                  f"(top-1 is {top.get('id')!s:.8} — {top.get('title', '')!r})")
            if rank == 1:
                print()
                print(f"SUCCESS: seeded trace is TOP-1 for the Clip-2 query.")
                print(f"trace id: {trace_id}")
                print(f"view:     https://commontrace.org/t/{trace_id}")
                return 0
        else:
            print(f"  attempt {attempt}: not searchable yet "
                  f"(got {len(ids)} results; embedding may still be processing)")
        time.sleep(POLL_INTERVAL_S)

    print(file=sys.stderr)
    print(f"FAIL: seeded trace {trace_id} did not reach top-1 within "
          f"{POLL_ATTEMPTS} attempts.", file=sys.stderr)
    if best_rank is not None:
        print(f"Best observed rank was {best_rank}. Strengthen the trace content "
              f"to match the Clip-2 symptom more closely, then re-run.",
          file=sys.stderr)
    else:
        print("It never became searchable — embedding may still be processing; "
              "re-run in a minute, or check the API.", file=sys.stderr)
    print(f"trace id: {trace_id}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
