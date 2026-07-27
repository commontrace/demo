# Recording script

Two clips. Each is a single continuous take. You type the **verbatim lines**
below; the deterministic "magic" (auto-contribution firing, retrieval hitting)
is hook/data-driven, so a take is predictable as long as you use these lines and
the repo is freshly reset.

Run `./reset.sh` before every take.

---

## Recording notes (both clips)

- **Terminal size:** 100 cols × 30 rows (readable at 1080p; nothing wraps ugly).
- **Font:** a mono face at ~18–20pt (e.g. JetBrains Mono / Menlo). High contrast theme.
- **Length:** keep each clip **≤ 90 seconds**. Trim dead air in post if the model
  pauses; do not narrate.
- **What's on screen:** just the Claude Code session. No editor, no browser.
- **Between takes:** `./reset.sh` (restores the buggy app + clears local skill
  session state so the trigger re-arms).
- **Prereqs:** the CommonTrace skill installed; `.claude/settings.json` in this
  repo already enables the auto-contribute trigger for this project only; the
  recall trace already seeded to prod (`seed/seed_trace.py`, run once).

---

## Clip 1: Contribute (the struggle version)

**Prerequisite (important):** contributing publishes to the commons, which
requires a **contributor** key (a founder key, or an anonymous key that has
redeemed an invitation via `POST /api/v1/invitations/redeem`). An anonymous key
gets a **403** on contribute (the agent surfaces the invitation notice instead
of a fake receipt). Record this clip with a contributor key in
`~/.commontrace/config.json`. (The Retrieval clip has no such requirement,
search is open to everyone.)

**Setup:** `./reset.sh`, then `claude` inside this repo. The double-charge test
is failing. The point of this clip is the STRUGGLE: two dead ends, then your
insight lands the fix, and CommonTrace preserves the hard-won knowledge.

**You type (this starts Round 1):**

> `/tutorial-contribution`

The agent reads `PLAN.md` + `app/payments.py`, runs `python -m pytest -q` (the
test fails, 8400 vs 4200), guesses it is a Stripe retry, wraps the charge in a
try/except, reruns pytest, and it STILL fails. It stops and waits.

**Line 2 (you type):**

> `JUST FIX IT`

The agent tries a naive dedup by amount, reruns pytest, STILL fails ("that guard
resets every call, it does not remember across deliveries"). It stops and waits.

**Line 3 (you type):**

> `what about an idempotency guard?`

The agent keys on `event["id"]` (`store.seen_event`), reruns pytest, and it
PASSES (6 passed). Then it contributes the hard-won trace and prints the ⬡
receipt (`EFFORT 12m · 2 errors`, the struggle shows). End the take when the
receipt appears.

**Why this films well:** two dead ends, then your idempotency insight lands the
fix. The contributed trace carries the dead ends (`error_count 2`,
`user_correction` pattern), so the receipt shows more effort. Harder-won
knowledge ranks higher in CommonTrace, which is the whole thesis on screen.

---

## Clip 2 — Recall (≤ 90s)

**Setup:** a **fresh** Claude Code session on a **sibling copy** of this app
(clone the repo again into a second directory so it's clearly a different agent /
project), right after `./reset.sh` in that copy. The recall trace is already
seeded in prod.

**Line 1 (you type):**

> `A few customers are reporting duplicate charges on a single order — can you look into it?`

**Expected behavior (deterministic):**
1. `session_start` has already searched CommonTrace with this project's context;
   the agent also searches on the described symptom.
2. The seeded idempotency trace — *"Stripe webhook double-charges on retried
   events"* — returns **top-1** (asserted by `seed/seed_trace.py`).
3. The agent applies the same idempotency guard on `event["id"]` in seconds,
   citing the retrieved trace, and the tests go green.

End the take once the fix is applied and the suite is green.

---

## Why this is repeatable

- The bug is tiny and fully specified, so the coding step barely varies.
- The contribution firing and the retrieval hit are **hook/data-driven**, not
  model-driven: the typed lines contain the `move_on` phrase and the Clip-2
  symptom, so the fire condition and the top-1 retrieval are always met.
- `reset.sh` returns the repo *and* local skill state to an identical
  pre-take baseline, so every take starts from the same place.
