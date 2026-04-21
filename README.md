# CuttleAgent

This repo now includes a sample Cuttlefish control service for a shared remote host.

The sample project uses:

- `FastAPI` as the HTTP control plane
- `SQLite` for lease and instance state
- a `CuttlefishServerManager` for leases, quotas, and cleanup
- a `CuttlefishCliManager` for host-side `cvd` calls, with override points for older `launch_cvd` setups

## Why HTTP

HTTP is the right default control plane here:

- it is easy for humans, scripts, and future LLM clients to use
- auth, logging, retries, and reverse proxying are standard
- you can add SSE or WebSockets later for boot logs without changing the core API

## Layout

- `src/server/api.py`: FastAPI app and routes
- `src/server/server_manager.py`: lease lifecycle and policy
- `src/server/cli_manager.py`: configurable Cuttlefish command runner
- `src/server/repository.py`: SQLite persistence
- `src/server/models.py`: API and domain models
- `src/server/config.py`: environment-based settings

## Run

Install dependencies and start the API:

```bash
uv sync
uv run uvicorn src.server.api:app --reload
```

The sample defaults to `CUTTLEFISH_DRY_RUN=true`, so it can be exercised without a real host launch.
When you are ready to point it at a real server, set `CUTTLEFISH_DRY_RUN=false` and adapt the command settings.
The sample defaults to the newer `cvd create` / `cvd stop` / `cvd remove` flow, but you can override the binaries with environment variables if your host still uses `launch_cvd`.

## Example

Create an instance:

```bash
curl -X POST http://127.0.0.1:8000/v1/instances \
  -H 'Content-Type: application/json' \
  -d '{
    "owner_id": "alice",
    "profile": "browser",
    "lease_minutes": 60,
    "overrides": {
      "cpus": 4,
      "memory_mb": 8192,
      "extra_args": ["--report_anonymous_usage_stats=no"]
    }
  }'
```

The response includes an `instance_id` and one-time `lease_token`. Send that token back in the `X-Lease-Token` header for later requests.

## Important Host Note

The API and lease manager are concrete. The exact host-side stop/remove semantics for Cuttlefish vary with how the host is configured.
This sample keeps those commands explicit and configurable instead of pretending one hardcoded command layout fits every deployment.
It assumes one lease maps to one `cvd create --num_instances=1` invocation. If you launch grouped devices in one create call, your stop/remove behavior needs a different policy.
