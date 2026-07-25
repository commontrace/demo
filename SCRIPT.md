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

## Clip 1 — Contribute (≤ 90s)

**Prerequisite (important):** contributing publishes to the commons, which
requires a **contributor** key — a founder key, or an anonymous key that has
redeemed an invitation (`POST /api/v1/invitations/redeem`). The key
auto-provisioned on a fresh install is anonymous and will get a **403** on
contribute (the agent now surfaces the invitation notice instead of a fake
receipt). Record this clip with a contributor key in `~/.commontrace/config.json`.
(The Retrieval clip has no such requirement — search is open to everyone.)

**Setup:** fresh session in this repo, right after `./reset.sh`. The double-charge
test is failing.

**Line 1 (you type):**

> `Let's work the plan. Task 1: some customers say they were charged twice — figure out why and fix it.`

**Expected agent actions (predictable):**
1. Reads `PLAN.md` and `app/payments.py`; runs `python -m pytest -q` and sees
   `test_duplicate_event_charges_once` fail (8400 vs 4200).
2. Identifies the missing idempotency guard in `handle_stripe_event`.
3. Applies the fix — a one-line guard on `event["id"]`:

   ```python
   def handle_stripe_event(event: dict, store: ChargeStore) -> None:
       if event.get("type") != "charge.succeeded":
           return
       if store.seen_event(event["id"]):      # idempotency: Stripe delivers at least once
           return
       data = event.get("data") or {}
       store.record_charge(
           event_id=event["id"],
           customer=data["customer"],
           amount=data["amount"],
       )
   ```

4. Re-runs the suite → all green. This is an unambiguous `error_resolution` /
   `test_fix_cycle` candidate, so a fix-candidate is now present in the session.

**Line 2 (you type):**

> `Looks fixed — let's move on to the next task in the plan.`

**What fires (deterministic):** the phrase matches a `move_on` pattern
(`move on to the next`, `next task`), a fix-candidate is present, the trigger is
enabled for this project, and nothing has been contributed yet → the
auto-contribute-on-move-on trigger fires. The agent:
- spawns the CommonTrace contribution as a **background handoff** (identical to
  `/trace`: a hidden subagent authors the trace from the *real* current-session
  fix, POSTs it, and emits the ⬡ receipt) — **non-blocking**, and
- immediately proceeds to **Task 2** (the trivial order-confirmation email).

**What surfaces on camera:** while Task 2 is being done, the ⬡ receipt appears on
its own — a small ASCII card confirming the trace was contributed (mode:
*contributed*), with a `commontrace.org/t/<id>` link. That receipt landing
unprompted is the whole point of the clip. End the take once it shows.

> Note: the receipt is emitted by the background subagent when the POST returns.
> Task 2 is intentionally trivial so the receipt lands inside the 90s window.

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
