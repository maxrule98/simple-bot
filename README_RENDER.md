# Render deployment notes

This repo includes a `render.yaml` and small Dockerfiles to deploy the monitoring stack to render.com.

## Quick steps

1. Push your repository to GitHub (if not already).
2. On Render.com, create a new "Web Service" using your repo and choose "Deploy with a render.yaml (Manifest)" or connect the repo and let Render pick services from the `render.yaml` file.
3. Render will build the Dockerfiles listed in `render.yaml`:
   - `infra/render/grafana/Dockerfile` (Grafana with provisioning)
   - `infra/render/prometheus/Dockerfile` (Prometheus with repo config)
   - `infra/render/pushgateway/Dockerfile` (Pushgateway)

## Environment & Secrets

- Add your exchange API keys and other secrets via Render's Environment -> "Environment Variables / Secrets" for each trader service.
- For each trader service (there will be one service per strategy), set:
  - `STRATEGY_CONFIG` (path or name)
  - `STRATEGY_ID` (unique id)
  - `DATABASE_PATH` (consider Render Persistent Disk)

## Persistent Storage

- Prometheus and Grafana should use Render Persistent Disks to store TSDB and DB respectively. Configure disk sizes in the Render service settings (manifest includes small defaults).

## Healthchecks

- Configure a simple HTTP health check for Grafana (`/`) and Prometheus (`/-/ready`).

## Notes & Next Steps

- The `trader-bot-example` entry in `render.yaml` is a placeholder. Duplicate it and set the proper `dockerfilePath`/env vars for each strategy service you want to run on Render.
- If you prefer to run monitoring using official Render services (Marketplace / Docker images), you can instead create Prometheus/Grafana services manually and point them at the Pushgateway endpoint.

If you'd like, I can:

- generate per-strategy service entries in `render.yaml` using existing `config/strategies/*.yaml` files;
- add Render-specific health checks and readiness probes;
- or create a script to push the repo and trigger initial deploy via the Render API/CLI.
