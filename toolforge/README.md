# Toolforge deployment runbook

Tool: **`wikibias-analyzer`** → https://wikibias-analyzer.toolforge.org
ToolsDB credential user: `s57898` · database `s57898__wikibias`

## Architecture

```
build   npm run build ──► nuxt generate ──► backend/static/   (static SPA, ssr:false)
        pip install .  ──► wikipedia_sources_bias importable anywhere

runtime  ┌─ web (gunicorn+Flask) ─ serves SPA at / and JSON at /api/*
         │      reads cache, enqueues misses, answers 202 while pending
         └─ worker (continuous job) ─ the ONLY process that analyses
                                      writes results to ToolsDB
```

An analysis takes minutes, far longer than a request may live, so the web tier
never performs one. `analysis_cache` is both the cache and the queue; `status`
distinguishes them.

## First deploy

The build service clones a **public** git repo — it cannot read your laptop.

```bash
ssh toolforge
become wikibias-analyzer

# 1. Create the database (once). Two underscores exactly.
mariadb --defaults-file=$HOME/replica.my.cnf -h tools.db.svc.wikimedia.cloud \
  -e "CREATE DATABASE IF NOT EXISTS s57898__wikibias CHARACTER SET utf8mb4;"

# 2. Build the image from the public repo.
toolforge build start <public-repo-url>
toolforge build logs            # watch; first build pulls node + python

# 3. Create the tables.
toolforge jobs run schema --wait \
  --image tool-wikibias-analyzer/tool-wikibias-analyzer:latest --command schema

# 4. Start the web service and the worker.
toolforge webservice buildservice start --mount=none --mem 2Gi --cpu 1
toolforge jobs load jobs.yaml

# 5. Warm the demo corpus (queues; the worker does the work).
toolforge jobs run populate --wait \
  --image tool-wikibias-analyzer/tool-wikibias-analyzer:latest --command populate
```

`--mount=none` is deliberate: this tool has **zero** persistent volume claims,
so everything durable lives in ToolsDB and nothing is written to NFS.

## Redeploy

```bash
toolforge build start <public-repo-url>
toolforge webservice restart
toolforge jobs restart worker      # picks up the new image
```

## Observing

```bash
toolforge webservice logs -f
toolforge jobs logs worker -f      # build-service images log to k8s, not NFS
toolforge jobs list --output long
toolforge build quota ; toolforge jobs quota
kubectl describe resourcequotas    # ground truth for limits
```

Queue state:

```sql
SELECT status, COUNT(*) FROM analysis_cache GROUP BY status;
SELECT page_url, status, attempts, error FROM analysis_cache
 WHERE status = 'error' ORDER BY updated_at DESC LIMIT 10;
```

## Environment

The build service injects `TOOL_TOOLSDB_USER` / `TOOL_TOOLSDB_PASSWORD`;
`backend/config.py` derives host and database name from them, so no secret
belongs in the repo (which is public). Plain `DB_*` variables override, for
local development.

| Variable | Effect |
|---|---|
| `TOOL_TOOLSDB_USER` / `_PASSWORD` | injected by Toolforge; presence means "we are on Toolforge" |
| `DB_HOST` `DB_USER` `DB_PASSWORD` `DB_NAME` | explicit override, wins over the above |
| `SYNC_ANALYSIS` | run analysis inline in the request. Defaults on locally, **off** on Toolforge |
| `ALLOW_MOCK_ANALYSIS` | permit `backend/mock.py` to stand in. Defaults on locally, **off** on Toolforge |

`ALLOW_MOCK_ANALYSIS` defaulting to off is deliberate. The mock used to load via
a bare `except ImportError`, so any packaging mistake produced a green deploy
serving fabricated numbers as though they were measurements. It now fails loudly.

Set overrides with `toolforge envvars create NAME` — never a password in git.

## Local development

```bash
pip install -r requirements-dev.txt
npm run build                        # or: cd frontend && npm run dev
python backend/schema.py             # against a local MariaDB
gunicorn --chdir backend --bind 127.0.0.1:5000 app:app
```

`nuxt dev` proxies `/api` to `127.0.0.1:5000` via the nitro route rule. That
rule is **dev-only** — a static `generate` build has no Nitro server, which is
why Flask serves the SPA and the API from one origin in production.

## Rules this deployment has to satisfy

- Code is **MIT** (`LICENSE`, contributors in `AUTHORS.md`) and the repo is
  public — an OSI-approved licence and public source are hard Toolforge rules,
  not preferences.
- No third-party assets in the page. The Google Fonts `<link>` was removed for
  this reason (ToU §7); the map uses a bundled GeoJSON, not external tiles.
- No unauthenticated direct access to Cloud Services resources — the API only
  exposes derived analysis, never arbitrary SQL.
