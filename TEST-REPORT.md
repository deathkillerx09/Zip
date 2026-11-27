# Test report — AI Money Town v2.1

Run date: 2026-11-25
Environment: Linux sandbox, Python 3.12.3, FastAPI 0.165.0, pytest 8.x, Node.js 22.23.3 (used only for the generated JavaScript syntax check).
Command: `python -m pytest` from the project root (configured by `pytest.ini`).

```
92 passed, 0 failed, 0 skipped   (1 third-party deprecation warning)
```

The warning is Starlette's own `httpx` deprecation notice inside FastAPI's
`TestClient`; it is not produced by this project.

No test needs Ollama, a network connection, an API key, or a real payment
service. Every test uses a temporary SQLite database and a fake local-model
client. Tests never touch `data/town.db` (verified by hash before/after the run
and by a dedicated test).

## Results by area

| Area | File | Tests | Result |
| --- | --- | --- | --- |
| API startup, tasks, ideas, chat, persistence | `backend/tests/test_api.py` | 12 | pass |
| Business lifecycle, ledger, recovery, pipeline, scheduler reports | `backend/tests/test_phase2.py` | 20 | pass |
| Access gate | `backend/tests/test_security.py` | 1 | pass |
| Worker queue, retries, failures, stuck recovery | `backend/tests/test_worker_queue.py` | 12 | pass |
| Product files: generation, validation, storage, delivery | `backend/tests/test_deliverables.py` | 8 | pass |
| Financial safeguards | `backend/tests/test_finance_guards.py` | 8 | pass |
| Health, queue diagnostics, rate limits, snapshot consistency | `backend/tests/test_system_health.py` | 10 | pass |
| Town front-end bootstrap and gameplay bundle | `frontend/tests/test_city_bootstrap.py` | 8 | pass |
| Department plaque layout | `frontend/tests/test_department_layout.py` | 3 | pass |
| Visible-control wiring, worker strip, product links, styles | `frontend/tests/test_ui_wiring.py` | 10 | pass |

## What the new tests actually prove

**Worker and scheduler** (`test_worker_queue.py`)

1. An owner-created task is claimed and completed (the previous build left it
   `pending` forever).
2. A retryable model error requeues the task with backoff, increments `attempts`,
   stores `last_error`, writes a `retry_scheduled` task event, and does not run
   again before the retry window opens.
3. A non-retryable error marks the task `failed`, keeps `completed_at` NULL,
   restores the employee to `available`, and writes a visible activity line.
4. Repeated failures stop at the configured attempt cap.
5. A model reply shorter than 30 characters is treated as a failure, not work.
6. With Ollama offline the worker does nothing and the queue reports the real
   reason.
7. A task stuck `in_progress` for longer than the window is requeued; beyond the
   attempt cap it becomes `failed`.
8. The queue honours priority.
9. A failed task cannot be moved to `completed` through the API.
10. Owner retry/run-now endpoints work and leave an event trail.
11. A missing chat model leaves the task `pending` with a clear message and does **not** consume an attempt, so installing a model later makes the queue run.

**Product files** (`test_deliverables.py`)

* A valid single-file application is written to `workspace/products/…` with
  `index.html` and `manifest.json`, hashed and recorded; the task reports
  `product_files_built` and the business gets a `product_files_built` event.
* A prose-only reply completes the task but creates **no** deliverable and no
  "built" event; a `deliverable_rejected` event is recorded instead.
* An invalid page is rejected (remote script, `{{ placeholder }}`, no controls,
  too small) and one repair round is attempted.
* The preview route serves the file with a `sandbox` CSP; the download route
  refuses `../` traversal.
* The build endpoint refuses callers without the owner token and records nothing
  when validation fails.

**Finance** (`test_finance_guards.py`)

* An identical settlement is refused; a duplicate expense reference is refused;
  a duplicate withdrawal request is refused; an over-refund is refused.
* Simulated estimated revenue of $9,000 leaves actual revenue and available funds
  at $0 and cannot fund an expense.
* An expense larger than verified funds is refused even with a raised limit.
* `spent_today_cents` and `spending_remaining_today_cents` are accurate.
* Ledger rows are immutable (an `UPDATE` raises).

**System** (`test_system_health.py`)

* `/api/system/health` reports database, workspace writability, scheduler,
  Ollama, queue, model roles and limits.
* `/api/system/queue` explains a blocked worker.
* `/api/city/state` is internally consistent (eight tasks always means eight
  employees with a current task) across repeated calls.
* Rate limiting returns `429` with `Retry-After`; an oversized body returns `413`.
* Unknown resources return `404`; owner routes are locked without a token; the
  site-wide Basic Auth gate covers the new endpoints.
* Importing `backend.app.main` in a subprocess creates no database file (this
  was a real bug: the previous module migrated the owner's database on import).

**Front-end** (`test_ui_wiring.py`, `test_city_bootstrap.py`, `test_department_layout.py`)

* Every `<button id=…>` in `index.html` has a handler in the scripts, and every
  `<form id=…>` is referenced by the app.
* Failure rendering, retry/run controls, attempt counts and error text exist.
* The business dialog lists built product files, links to preview/download, and
  offers the owner-triggered build.
* Graphics quality, zoom and recenter are wired in the renderer that actually
  runs; the render status is no longer stuck on "Checking 3D scene…".
* The Three.js bundle is opt-in, not downloaded by default.
* Department plaques do not overlap at 1564×855, 1280×700, 1024×650 or 800×600.

## Manual browser verification

The app was started locally (`uvicorn app.server:app`) and clicked through in
Chrome with Ollama deliberately offline:

* Town map rendered with live HUD metrics (8 employees, 0 working, 8 queued,
  $0.00 funds, 0 products) and a live sync line.
* Zoom in/out, Recenter, Graphics Low→High all changed the view; the status line
  reflected the chosen quality.
* Entering the Ideas Workshop showed the interior, the live department board and
  the assigned teammate; *Return to town* worked.
* Opening the teammate conversation worked; sending a message produced an honest
  failure ("Cannot reach local Ollama… Is it running?") and no fabricated answer.
* Dashboard showed the worker strip with the exact blocking reason, the task
  board with **Run now** controls and status selects.
* Business Empire and the Treasury rendered real ledger values ($0.00, spending
  limit $0, no bank connected) and owner controls.

Not exercised interactively: owner-token entry (the browser policy forbids typing
into password fields), product builds (they need a local model), and Windows
`.bat` execution (this environment is Linux).

## Reproducing

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
python -m pytest -q
```

Optional: install Node.js to enable the JavaScript syntax check on generated
product files. Without Node that single check is skipped and recorded as
`"javascript": {"ran": false, …}` — the other validation checks still apply.

## What the suite does not prove

Automated tests cannot prove that a specific local model produces good prose, how
fast it runs on your laptop, or that a generated product is commercially useful.
They prove the machinery around the model: it runs the right work, stores real
output, refuses to fake success, keeps the ledger honest, and keeps the owner in
control. See `KNOWN-LIMITATIONS.md`.
