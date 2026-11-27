# AI Money Town - final local setup

## Start and stop

1. Extract this ZIP into a new folder (do not overwrite your only copy of `data\town.db`).
2. Double-click **`Start AI Money Town.bat`**. The first run creates a Python
   environment, installs dependencies, backs up the database once, writes a private
   owner token to `.owner-token`, and starts the server.
3. Open `http://127.0.0.1:8000` (the launcher opens it for you).
4. To stop, double-click **`Stop AI Money Town.bat`**, or press `Ctrl+C` in the
   black server window.

Leave the terminal window open while you use the town. Closing it stops the app.

## Model setup (one time)

```powershell
ollama pull qwen3.5:0.8b
ollama pull qwen3:4b
```

The launcher uses the small model for chat and idea batches and prefers `qwen3:4b`
for research and product files. A model that is not installed falls back
automatically; the app never downloads or pays for a model on its own.

## Owner actions

Owner-only actions (idea approval, lifecycle transitions, ledger entries, spending
limit, product builds, task retry/run) need the token in `.owner-token`. Paste it
into the **Treasury** panel; it is kept in that browser tab only.

## What you should see

- The town map with live counts: employees, working, queued, businesses, funds,
  products built.
- A worker strip on the Dashboard that says either "Worker ready" or the exact
  reason it is blocked (Ollama offline, no model installed, nothing queued).
- Eight starter assignments. They move from **queued** to **working** to
  **completed** only when the local model actually returns a result. If the model
  is missing you will see queue reasons, not fake progress.
- Task cards show attempts, the last error and, for failures, a **Retry** button.

## If work stays queued

Open `http://127.0.0.1:8000/api/system/queue` or read the worker strip. The
`blocked_reason` field states the problem. Common causes:

- Ollama is not running -> start it, the launcher does this automatically when it
  can find `ollama.exe`.
- No model installed -> `ollama pull qwen3.5:0.8b`.
- Model too large / very slow -> try a smaller model or raise
  `OLLAMA_TASK_TIMEOUT_SECONDS`.
- Many queued tasks -> expected on a laptop; one task runs at a time.

## Tests

```powershell
.venv\Scripts\python.exe -m pytest -q
```

92 tests pass without Ollama. See `TEST-REPORT.md`.

## Data

`data\town.db` is your save file and is migrated in place on first start of a new
version; existing tasks, ideas, businesses and ledger rows are preserved. Keep a
backup before moving folders. Generated product files live in `workspace\products`.

## Cloud

`Dockerfile`, `docker-compose.yml`, `Caddyfile` and `.env.cloud.example` prepare a
private HTTPS deployment. Read `CLOUD-DEPLOYMENT-READINESS.md`. Nothing is
provisioned; no paid service is required or enabled.
