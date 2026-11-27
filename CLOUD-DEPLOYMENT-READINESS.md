# Cloud deployment readiness

This project now has a Dockerfile, Docker Compose stack, Ollama service, persistent named volumes, and Caddy HTTPS reverse proxy configuration. These files prepare deployment; they do **not** create a cloud account, provision a server, or guarantee always-free uptime.

## What the stack contains (v2.1)

- `web` — the FastAPI app, served by `uvicorn app.server:app`. Persistent
  `town_data:/app/data` (database) **and** `workspace_data:/app/workspace`
  (generated product files) volumes.
- `ollama` — local models inside the compose network. The app reaches it through
  `OLLAMA_BASE_URL=http://ollama:11434`, which requires
  `AI_MONEY_TOWN_ALLOW_REMOTE_OLLAMA=1`. That flag exists only for a private
  container network: never publish port 11434 or point it at a public host.
- `caddy` — automatic HTTPS for `DOMAIN`.
- Request guards are on in production: 240 write/expensive requests per minute per
  client and a 2 MB body cap. Adjust with
  `AI_MONEY_TOWN_RATE_LIMIT_PER_MINUTE` and `AI_MONEY_TOWN_MAX_BODY_BYTES`.

Health check for uptime monitors or a load balancer:

```
GET https://<domain>/api/system/health    (with the site Basic Auth credentials)
```

It returns HTTP 200 with `database.ok`, workspace writability, scheduler state,
the local model list and the queue's blocking reason. A `200` with
`"ollama": {"connected": false}` means the site is up but AI work is paused —
not a crash.

Restart behaviour: `restart: unless-stopped` on every service. On restart the app
requeues unfinished tasks (attempt counts preserved), recovers stale claims, and
keeps all data in volumes.

Backup: stop the stack, then archive both volumes (`town_data` and
`workspace_data`) plus the `.env` file. Restore by putting them back before
starting.

## Security prerequisites

- Set `DOMAIN`, `AI_MONEY_TOWN_ACCESS_USERNAME`, `AI_MONEY_TOWN_ACCESS_PASSWORD`, and `AI_MONEY_TOWN_OWNER_TOKEN` in a private server-side `.env` file.
- The optional site-wide Basic Auth gate protects pages, static assets, and APIs when both `AI_MONEY_TOWN_ACCESS_USERNAME` and `AI_MONEY_TOWN_ACCESS_PASSWORD` are configured. It is applied before every route, including the health and product-file routes.
- Generated product previews are served with `Content-Security-Policy: sandbox …`, so a generated page runs in a unique origin and cannot read the town's API, cookies or storage.
- Keep the owner token separate from the site password.
- Do not upload `.env`, `.owner-token`, or a local database into a public repository.
- Before exposing the app publicly, review API authorization, backup/restore, payment-provider rules, and the applicable account-age requirements.

## Local container smoke test

1. Install Docker Desktop.
2. Copy `.env.cloud.example` to `.env` and replace every placeholder with private values. Use a domain whose DNS A/AAAA records point to the host.
3. Run `docker compose up -d --build`.
4. Pull the small model into the private Ollama service: `docker compose exec ollama ollama pull qwen3.5:0.8b`.
5. Check `docker compose logs -f web ollama caddy`.
6. Visit the configured HTTPS domain.

The application database is stored in the `town_data` named volume. Ollama models are stored in `ollama_data`. Back up both volumes before upgrades. The local Windows `data/town.db` is deliberately excluded from the image build; migrate it only through an intentional, backed-up restore step.

## Always-free host reality

A persistent always-on VM is the closest fit for the scheduler + Ollama design. Oracle currently advertises Always Free compute and block storage, but eligible shape availability varies by region, and Oracle documents that idle Always Free compute instances may be reclaimed based on low CPU/network/memory usage over a seven-day window. Check the current Oracle Console limits and terms when creating the server; do not select paid shapes or upgrade billing.

Render's current free web services spin down after 15 minutes without inbound traffic, and their local filesystem is ephemeral. That makes a free Render web service unsuitable for a continuously running worker with a local SQLite database.

Even with an Always Free VM, uptime, capacity, storage, bandwidth, and model speed are not guaranteed forever. If free compute is unavailable or reclaimed, the app should be paused rather than silently upgraded or charged.

## Model and workload notes

The Compose stack runs Ollama beside FastAPI. It defaults all three roles to a small 0.8B model to keep RAM use low. You can later test a stronger worker model after monitoring memory and inference speed. The 50-ideas/hour setting is a target; actual useful unique ideas depend on CPU, model latency, duplicate filtering, and whether the scheduler is busy. A million-customer simulation is synthetic analysis, not a million real people or guaranteed demand.

## Product files on a server

Generated products are written to `/app/workspace/products/…`. Without the
`workspace_data` volume they would vanish on every redeploy. The container image
creates the folder; the volume keeps it.

## Deployment status

- Container files: prepared.
- Persistent volumes: configured.
- HTTPS reverse proxy: configured for a real domain.
- Private site gate: implemented and tested.
- Cloud account / server: not provisioned.
- DNS / secrets: not configured.
- Real bank or payout provider: not connected.
