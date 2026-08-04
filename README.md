# CommonTrace Demo — Stripe double-charge

A tiny, reproducible payments service with a **real bug**: a Stripe webhook handler
that has no idempotency guard, so a retried or duplicated `charge.succeeded` event
charges the customer **twice**.

This repo is the reproduction kit behind the two screencasts at
[commontrace.org/demo](https://commontrace.org/demo):

1. **Contribute** — an agent finds and fixes the double-charge, you say "let's move on
   to the next task," and CommonTrace *automatically* contributes the just-learned fix
   in a background subagent. The ⬡ receipt surfaces on its own.
2. **Recall** — a *different* agent hits the same double-charge and CommonTrace surfaces
   the prior fix instantly, no manual search.

Together they show the flywheel: agent A's fix becomes agent B's instant knowledge.

## Record it (fastest path)

Both clips are driven by slash commands from the CommonTrace skill — you type one
command and film; the agent runs the whole scenario and prints the ⬡ receipt.
Full runbook: **[commontrace.org/tutorial](https://commontrace.org/tutorial)**.

```
claude                     # open Claude Code inside this repo
/tutorial-contribution     # clip 1 — fix the double-charge, watch it get contributed
/tutorial-retrieval        # clip 2 — recall another agent's fix instantly
```

No venv, no `pip install`, no `./reset.sh`. The slash commands reset the repo to its
buggy baseline themselves at the start of every run, and the test suite is
`unittest`-based so it runs on a stock Python 3.10+. (The verbatim, type-it-yourself
walkthrough is in [`SCRIPT.md`](SCRIPT.md); `./reset.sh` is still there if you want to
reset by hand.)

## What's in here

| Path | What it is |
|------|-----------|
| `app/payments.py` | The webhook logic — `handle_stripe_event()` + `ChargeStore`. **Ships buggy on purpose.** |
| `app/api.py` | A small FastAPI wrapper (`POST /webhooks/stripe`) so it reads like a real service. **Optional** — nothing in the demo needs it. |
| `tests/test_payments.py` | Unit tests, standard library only. `TestCharges::test_duplicate_event_charges_once` **fails on `main`** — that's the bug the demo fixes. |
| `tests/test_api.py` | HTTP smoke test. Skips itself when fastapi/httpx are not installed. |
| `PLAN.md` | The two-task plan the agent works through on camera. |
| `SCRIPT.md` | The verbatim lines to type for each clip + recording notes + expected agent actions. |
| `reset.sh` | Restores the repo + local skill state to a clean pre-take state so takes repeat. |
| `.claude/settings.json` | Enables the auto-contribute-on-move-on trigger **for this project only**. |
| `seed/seed_trace.py` | Seeds the recall trace into prod CommonTrace (run once, manually, with a contributor key). |

## Try it yourself

You need [Claude Code](https://claude.com/claude-code) and the CommonTrace skill.

```bash
# 1. Clone
git clone https://github.com/commontrace/demo.git
cd demo

# 2. See the bug (the double-charge test fails on purpose).
#    Standard library only — no venv, no pip install.
python3 -m unittest -q          # or: python3 -m pytest -q, if you have pytest

# 3. Open Claude Code here, install the skill, run the demo
claude
```

Then, inside Claude Code:

```
/plugin marketplace add commontrace/skill
/plugin install commontrace@commontrace
/tutorial-contribution
```

Publishing a trace needs a **contributor** key. If you already have one, pass it at
install time and skip the config file entirely:

```
/plugin install commontrace@commontrace --config api_key=ct_...
```

Without one you still get the full run: the command detects an anonymous key up front
and offers the Retrieval clip, which needs no key at all.

The double-charge test is **expected to fail on a fresh clone** — fixing it is the point.
The slash commands restore that buggy baseline themselves before each run, so takes
repeat without any manual reset.

Want the HTTP layer too? `pip install -r requirements.txt` in a venv also enables
`tests/test_api.py`, which otherwise skips itself.

## The bug, in one sentence

`handle_stripe_event()` records a charge for every `charge.succeeded` event it receives,
with no idempotency key on `event["id"]` — so Stripe's at-least-once delivery
(retries + duplicates) double-charges. The fix is a one-line guard.
