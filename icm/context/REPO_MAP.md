# REPO MAP — PAULIS-PLACE / Yappyverse Factory

> File: `icm/context/REPO_MAP.md`

## Backend (`backend/`)
```
backend/
  main.py                  FastAPI app, router registration, WebSocket /ws
  config.py                pydantic BaseSettings, reads .env
  start.py / start_worker.py   entry points (uvicorn + celery)
  api/                     HTTP routes (FastAPI routers)
    dashboard.py / products.py / tasks.py / approvals.py
    research_lab.py / payments.py / council.py / memory.py
    health.py (NEW, R-01..R-07 healthchecks + envelopes)
  agents/                  SSSF role implementations (5 roles per spec 03)
    research_agent.py      = SCANNER
    idea_factory.py        = SCORER
    design_agent.py        = DESIGNER
    council_agent.py       = ADVOCATE + CRITIC driver
    publisher_agent.py     = PUBLISHER
    watcher_agent.py       = SAFETY_JUDGE for voice + ops
    memory_aware.py        = LEDGER + patterns writer
    autoresearch_agent.py  = research scout (aux)
  services/                external integrations
    ai_service.py          LiteLLM/OpenRouter wrapper (all model calls go here)
    profile_router.py (NEW) declares task profile -> model
    model_router.py (existing)  (refactor -> delegate to profile_router)
    zernio_service.py (NEW) Zernio REST + auth flow
    printify_service.py / etsy_service.py / fiverr_service.py
    payment_service.py / wiki_service.py / trends_service.py
    browser_view_service.py / evolving_memory.py
  workers/                 celery tasks + beat schedule
    celery_app.py          broker=Redis, backend=Redis
    tasks.py               scan_all_trends / score_hot_trends / create_products_from_trends
    boot_task.py           startup idempotent bot
  models/                  SQLAlchemy
    base.py / product.py / task.py / trend.py / research.py
    ledger.py (NEW)        payment + ledger entries
    decision.py (NEW)     council rulings persisted
    avatar.py (NEW)        3D avatar state for lounge
  prompts/                 role prompt files (legacy, migrated to icm/instructions/)
  alembic/                 DB migrations
  cli/  (NEW)              `python -m backend.cli` replay / shipcheck / sweep
```

## Frontend (`frontend/`) — Next.js 15 App Router
```
frontend/src/app/
  page.tsx                 dashboard
  products/                product feed
  trends/                  trend monitor
  research/                research lab
  tasks/                   queue
  observation/             ops report viewer
  settings/                env + agent settings
  lounge/ (NEW)            3D Three.js Paulie's Place
  api/health/route.ts (NEW) client-side health reporter
frontend/src/components/
  lounge/ (NEW)            ThreeScene, Avatar, VoiceCmd
  shared/                  layout, sidebar, topbar
frontend/src/lib/          api client + ws client
```

## ICM (`icm/`) — model-agnostic context layer
See `icm/context/REPO_MAP.md` (this file), `EVENT_BUS.md`, `ENVELOPES.md`, `CHARACTER_REGISTRY.md`, `OPEN_BRAIN_SCHEMA.md`.

## Infrastructure
- `docker-compose.yml` — postgres + redis + backend + worker
- `vercel.json` — frontend hosting
- `scripts/` — ops
- `alembic.ini` — DB migrations