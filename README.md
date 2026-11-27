# AI Money Town

A local-first, autonomous AI business simulation for Windows 11. Eight named AI
employees work through a real pipeline — idea discovery, research, strategy,
product building, simulation, launch readiness — on your own hardware, using
your own local Ollama models. It has a persistent SQLite database, a virtual
accounting ledger with hard spending safeguards, a scheduler that executes real
queued work, and an interactive isometric town you can click through.

Everything runs on `127.0.0.1`. There is no paid API, no cloud AI, no bank
connection, and no way for the town to spend your personal money.

---

## What this build changed (v2.1)

This build repairs the pipeline end to end rather than restyling it. The
headline fixes came from a full audit of the previous source:

1. **Tasks typed by you never ran.** The scheduler only claimed autonomous
   tasks, so anything created on the Task Board sat `pending` forever. The
   worker now executes owner tasks too, using the employee's role for
   instructions.
2. **Failures were invisible.** Tasks could not even be recorded as failed. There
   is now a real `failed` status, per-task attempt counting, a stored
   `last_error`, a `task_events` audit trail, retry backoff, and an attempt cap —
   plus a visible "why it failed" line on the task card.
3. **Stuck work never recovered while the server stayed up.** A task abandoned by
   a crashed worker thread was lost. Stale `in_progress` tasks are now recovered
   after 15 minutes (configurable) or failed if they have used their attempts.
4. **The Product Builder produced prose, not products.** Development tasks now
   ask the model for a real single-file application, validate it (structure,
   offline-only assets, placeholders, JavaScript syntax via Node when present),
   repair once, and save it under `workspace/products/…` with a manifest,
   checksum and database record. A blueprint alone is never reported as a built
   product.
5. **One inconsistent dashboard read.** `/api/city/state` could show eight tasks
   while every employee looked unassigned, because each `SELECT` had its own
   snapshot. Read endpoints now use a single explicit read transaction.
6. **Importing the module migrated your real database.** `backend/app/main.py`
   created the app at import time, so running the tests opened and migrated
   `data/town.db`. The ASGI app now lives in `backend/app/server.py`; importing
   the application code touches nothing.
7. **Dead controls.** The Graphics selector, render status, refresh, close and
   return buttons did nothing in the renderer actually used. All are wired, and
   a test fails if any button in `index.html` loses its handler.
8. **Wasteful startup on integrated graphics.** The 560 KB Three.js bundle was
   downloaded and rendered (then hidden) on every launch. It is now opt-in
   (`localStorage["ai-money-town-renderer"] = "3d"`), so the isometric renderer
   is the only one running by default.
9. **Ledger duplicate gaps.** Identical settlements, repeated expense references
   and repeated withdrawal requests are now refused. Today's spend and remaining
   allowance are reported in the summary.
10. **Idea-generation errors were only in the server log.** A failed batch is now
    recorded as a report with the model, the error and the reply excerpt, and
    shows in the activity feed.

---

## Quick start (Windows 11)

1. Install **Python 3.11+** (tick *Add Python to PATH*).
2. Install **Ollama for Windows**, then pull a model once:
   `ollama pull qwen3.5:0.8b` (add `ollama pull qwen3:4b` for better product work).
3. Extract the project folder and double-click **`Start AI Money Town.bat`**.
4. Leave the terminal open. The browser opens `http://127.0.0.1:8000`.
5. To stop it, double-click **`Stop AI Money Town.bat`** (or press `Ctrl+C`).

The launcher creates `.venv`, installs `backend/requirements.txt`, creates a
one-time database backup, creates a private owner token in `.owner-token`, starts
Ollama if it is installed but stopped, and serves the app on `127.0.0.1:8000`.
Paste the token into the Treasury panel to unlock owner actions for that tab.

### Manual start

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
$env:AI_MONEY_TOWN_OWNER_TOKEN = "a-long-random-secret"
uvicorn app.server:app --app-dir backend --host 127.0.0.1 --port 8000
```

Interactive API docs: `http://127.0.0.1:8000/docs`.

---

## How work actually runs

```
owner task / idea research / stage assignment
        ↓
scheduler cycle (default every 20 s)
        ↓
claim → local model call → validate → save result → next stage
        ↓                            ↘ on error
   completed                        retry with backoff (up to 3 attempts)
                                     ↳ then `failed` with a stored reason
```

* **One model call at a time.** Chat always wins: an interactive message takes
  the lock, background work waits. This is what keeps a slow model from freezing
  the laptop.
* **Every completed task has a persisted result.** A task becomes `completed`
  only after a non-empty, validated reply is written to the database.
* **Idea → business pipeline.** `idea_research → idea_strategy → research →
  development → simulation → ready_for_approval`. It stops there. Nothing is
  published, sold, or launched without your explicit approval.
* **`ready_for_approval` is a stop sign.** A real-world launch is an owner
  action (`POST /api/businesses/{id}/transition` with the owner token), never
  automatic.

## Real product files

`workspace/products/business-<id>-<slug>-<deliverable-id>/` holds the generated
`index.html` plus `manifest.json`. The validator rejects pages that are too
small, reference remote scripts or fonts, still contain `{{ }}` / `TODO` /
`Lorem ipsum` placeholders, have no interactive element, or contain JavaScript
with a syntax error (checked with Node when it is installed). Open one through
`/api/deliverables/{id}/preview`, which serves it with a `sandbox` CSP: the page
runs in a unique origin and cannot read your town data, cookies or API.

`POST /api/businesses/{id}/products/build` builds on demand (owner token). It
returns `201` with the deliverable, `422` when the model's output failed
validation (nothing is recorded), or `503` when the model is unavailable.

## Employees

| Employee | Role | Main responsibilities |
| --- | --- | --- |
| Mayor Wafflebeard | Mayor | Priorities, coordination, approval review |
| Sherlock Beans | Trend Detective | Idea research, market assumptions, revival investigation |
| Captain Spreadsheet | Idea Strategist | Evaluation, risk, smallest safe test |
| Gizmo McNoodle | Product Maker | Product building and prototype files |
| Sir Hype-a-Lot | Marketing Wizard | Honest positioning drafts (never published) |
| Cash Moneybags | Banker & Treasurer | Virtual ledger, unit economics |
| Inspector Baguette | Quality Inspector | Quality, security and accessibility review |
| Bubbles McChat | Customer Helper | Support and feedback plans (never contacts anyone) |

Each has a persistent profile, task history, attempts, results, errors, and a
department workstation in the town map.

## Local AI configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Local Ollama. Non-loopback hosts require `AI_MONEY_TOWN_ALLOW_REMOTE_OLLAMA=1` (container network only). |
| `OLLAMA_CHAT_MODEL` | auto | Small fast model for conversations |
| `OLLAMA_IDEA_MODEL` | chat model | Idea batches |
| `OLLAMA_WORKER_MODEL` | chat model | Research/strategy/quality |
| `OLLAMA_MODEL_PRODUCT` | worker model | Product file generation |
| `OLLAMA_MODEL_RESEARCH` / `_FINANCE` / `_QUALITY` | worker model | Per-category overrides |
| `OLLAMA_TIMEOUT_SECONDS` | `55` | Single request timeout |
| `OLLAMA_TASK_TIMEOUT_SECONDS` | `110` | Background task timeout |
| `OLLAMA_KEEP_ALIVE` | `10m` | How long the model stays loaded |
| `OLLAMA_NUM_CTX` / `OLLAMA_NUM_PREDICT` | `1024` / `64` | Generation limits |

A model that is configured but not installed falls back to the next available
conversational model, and the model that actually ran is stored on the task.

## Scheduler and resource limits

| Variable | Default | Purpose |
| --- | --- | --- |
| `AI_MONEY_TOWN_SCHEDULER_SECONDS` | `20` | Cycle interval |
| `AI_MONEY_TOWN_SCHEDULER_START_DELAY_SECONDS` | `10` | Head start before the first model call |
| `AI_MONEY_TOWN_TASK_CONCURRENCY` | `1` | Model calls in flight (kept at 1) |
| `AI_MONEY_TOWN_TASK_MAX_ATTEMPTS` | `3` | Attempts before `failed` |
| `AI_MONEY_TOWN_TASK_RETRY_SECONDS` | `45` | Base retry backoff (doubles) |
| `AI_MONEY_TOWN_STALE_TASK_SECONDS` | `900` | Stuck-task recovery window |
| `AI_MONEY_TOWN_IDEA_TARGET_PER_HOUR` | `50` | Idea throughput target (not a guarantee) |
| `AI_MONEY_TOWN_IDEA_BATCH_SIZE` | `10` | Ideas requested per batch |
| `AI_MONEY_TOWN_IDEA_INTERVAL_SECONDS` | `720` | Batch cadence |
| `AI_MONEY_TOWN_SIMULATED_CUSTOMERS` | `10000` | Synthetic profiles per simulation |
| `AI_MONEY_TOWN_RATE_LIMIT_PER_MINUTE` | `240` | Write/expensive-request cap per client |
| `AI_MONEY_TOWN_MAX_BODY_BYTES` | `2097152` | Request body cap |
| `AI_MONEY_TOWN_WORKSPACE` | `./workspace` | Generated product files |

Work is paused automatically above 95 % memory use, and no remote AI service is
ever called.

## Money and approval boundaries

* The Central Bank is a **virtual ledger**, not a bank account. No payout or
  payment provider is connected.
* Pending receipts never count as revenue. Settlement needs the owner token and
  an external evidence reference, and the resulting records are append-only
  (database triggers refuse `UPDATE`/`DELETE`).
* Expenses and reinvestment need **available verified earnings** *and* a non-zero
  owner-set daily limit. The limit authorises nothing by itself.
* A withdrawal request is recorded only. It is never executed and never reported
  as transferred.
* Simulated revenue, synthetic customers, morale, XP and trophies are labelled
  simulations everywhere they appear and never touch real balances.
* The town cannot spend your personal money, take loans, or start subscriptions.

## API map (main routes)

| Route | Purpose |
| --- | --- |
| `GET /api/dashboard`, `/api/city/state` | Consistent single-snapshot town state |
| `GET /api/system/health`, `/api/system/queue` | Subsystem health and *why* work is or is not moving |
| `GET/POST /api/tasks`, `PATCH /api/tasks/{id}` | Task board |
| `GET /api/tasks/{id}/events`, `POST …/retry`, `POST …/run` | Attempt history, requeue, run now (owner) |
| `GET /api/employees`, `/api/employees/{id}/profile` | Team and history |
| `POST /api/employees/{id}/messages[/stream]` | Local-model conversation (SSE supported) |
| `GET/POST /api/ideas`, `PATCH /api/ideas/{id}` | Idea intake (approval needs the owner token) |
| `GET /api/empire`, `/api/businesses/{id}` | Portfolio and full business history |
| `POST /api/businesses/{id}/transition` | Owner lifecycle control |
| `GET /api/businesses/{id}/deliverables`, `/api/deliverables…` | Built product files |
| `POST /api/businesses/{id}/products/build` | Owner-triggered real product build |
| `GET /api/finance/summary`, `/transactions` | Ledger truth |
| `POST /api/finance/…` | Owner-reconciled ledger events |
| `GET /api/management/reports` | Mayor review history |

Owner routes require `X-Owner-Token`. With no token configured they answer `503`
and stay disabled.

## Tests

```powershell
python -m pytest -q
```

92 tests pass (0 failed, 0 skipped) without Ollama and without a network
connection; they use temporary databases and a fake model client. See
`TEST-REPORT.md` for the breakdown and `KNOWN-LIMITATIONS.md` for what tests
cannot prove.

## Data, backup and the town map

* `data\town.db` is the save file. The app migrates it in place with additive,
  data-preserving changes; it never resets your town. Back it up before moving
  folders.
* `.owner-token` is a secret. Do not share it or commit it.
* The visible town is an isometric 2.5D canvas map: click a department plaque to
  glide in, click a teammate to talk, `Esc` or *Return to town* to leave. Deep
  links work too: `/?dept=research-lab`.
* The Three.js scene is still included as an experiment. Opt in once with
  `localStorage.setItem("ai-money-town-renderer", "3d")` in the browser console,
  or stay on the isometric renderer (recommended for Iris Xe graphics).

## Cloud (prepared, not deployed)

`Dockerfile`, `docker-compose.yml`, `Caddyfile` and `.env.cloud.example` describe
a private HTTPS deployment with persistent `data` and `workspace` volumes, a
site-wide Basic Auth gate, a separate owner token and container-network Ollama.
Read `CLOUD-DEPLOYMENT-READINESS.md`. Nothing is provisioned, nothing is
publicly exposed, and no paid service is required or selected.

## Project layout

```
backend/app/
  main.py          API routes, guards, owner authorization
  server.py        ASGI entry point (creates the app)
  database.py      Schema, additive migrations, snapshot reads
  scheduler.py     Queue, retries, failure handling, idea batches, reviews
  deliverables.py  Product file generation, validation and storage
  ollama.py        Local model client, retries, JSON repair, model routing
  empire.py        Business lifecycle, revival, recognition
  finance.py       Virtual ledger and spending safeguards
  people.py        Employee profiles and history
  market_simulation.py  Deterministic synthetic market exercise
frontend/          Dashboard, town map, employee chat, product links
workspace/products Generated product files (created at runtime)
backend/tests/ frontend/tests/   Automated tests
```
