# Green PM v5 — Engineering Project Intelligence Platform

> "Green PM continuously transforms every project event into synchronized project intelligence and actionable decisions."

## Status

| Branch | Purpose | Environment |
|---|---|---|
| `main` | v1 demo (legacy, preserved) | — |
| `dev` | v5 active development | [green-pm-sandbox on GCP](https://console.cloud.google.com/run?project=green-pm-sandbox) |

---

## v5 Architecture

**17 Engines. 24 Cloud Run services. Project Intelligence Graph at the core.**

- **Stack**: FastAPI (Python 3.12) · PostgreSQL 15 · PgBouncer (session mode) · Redis · Pub/Sub (27 topics) · Firestore · Next.js 14 · Cloud Run
- **Key pattern**: Transactional Outbox → Pub/Sub → Engine subscription → PIG update
- **Tenancy**: Row Level Security on all tables via `app.current_tenant_id` session variable

See [`docs/`](docs/) for the full v5 documentation set.

---

## Development Setup

### Prerequisites
- Docker + Docker Compose
- Python 3.12+
- Node.js 20+
- Google Cloud SDK (`gcloud`)

### Start local infrastructure

```bash
cp .env.example .env
make dev
```

This starts: PostgreSQL 15 · Redis 7 · Pub/Sub emulator · PgBouncer

### Apply migrations

```bash
make migrate
```

### Run tests

```bash
make test          # all tests
make test-rls      # RLS isolation verification (required before any PR merge)
make test-load     # k6 load baseline
```

### Run v1 legacy demo

```bash
docker compose --profile v1 up
# → Frontend: http://localhost:3000
# → Backend API: http://localhost:8080/docs
```

---

## Services (Phase 0)

| Service | Port | Status | Description |
|---|---|---|---|
| `api-gateway` | 8000 | Sprint 1 | JWT auth, routing, rate limiting |
| `core-platform` | 8001 | Sprint 1 | Tenants, projects, users, RBAC |
| `pig-service` | 8002 | Sprint 2 | Project Intelligence Graph |
| `outbox-worker` | — | Sprint 2 | Pub/Sub event publishing |
| `activity-workspace` | 8003 | Sprint 2 | First Entity Workspace |

---

## Repository Structure

```
green-pm/
├── docs/v5/
│   ├── architecture/    Engineering Architecture, Domain Model, PIG, Event Model
│   ├── technical/       Database Schema, API Contracts, Test Strategy
│   ├── implementation/  Engineering Standards, Phase 0 Epic, Sprint Backlog
│   ├── product/         Personas, User Journeys, Engine Workflows
│   └── wireframes/      34 screens, interactive HTML
├── docs/decisions/      Architecture Decision Records (ADRs)
├── services/            One directory per Cloud Run service
├── shared/              Shared SQLAlchemy base, event envelopes, test fixtures
├── migrations/          Alembic migrations (single set for all services)
├── tests/
│   ├── integration/     Real PostgreSQL, no mocks
│   ├── security/        RLS isolation tests (required per table)
│   └── load/            k6 load baseline scripts
├── infra/terraform/     GCP infrastructure as code
├── frontend/            Next.js 14 (v5 frontend — Phase 1+)
├── backend/             v1 legacy FastAPI (preserved)
├── .github/workflows/   CI (lint + test) + Deploy to dev (green-pm-sandbox)
└── Makefile             dev, migrate, seed, test, test-rls, test-load, lint
```

---

## CI/CD

**On PR to `dev`**: lint (ruff) + type check (mypy) + unit/integration tests

**On push to `dev`**: build Docker images + deploy changed services to `green-pm-sandbox` Cloud Run

**GCP project**: `green-pm-sandbox` · **Region**: `asia-south1`

### GitHub Secrets required for deployment

| Secret | Description |
|---|---|
| `GCP_SA_KEY` | Service account JSON key (base64 not required — paste raw JSON) |

To create the key:
```bash
gcloud iam service-accounts keys create key.json \
  --iam-account=729630816551-compute@developer.gserviceaccount.com \
  --project=green-pm-sandbox
```
Then add the contents of `key.json` as the `GCP_SA_KEY` secret in GitHub repo Settings → Secrets → Actions. Delete the local `key.json` after.

---

## Engineering Standards

Read [`docs/v5/implementation/GreenPM_v5_Engineering_Standards.docx`](docs/v5/implementation/GreenPM_v5_Engineering_Standards.docx) before writing any code. It defines: entity vs event vs value object taxonomy, PIG usage rules, event design rules, service boundary rules, ID generation, mutability, consistency SLOs, tenancy/security rules, and testing standards.

**The two rules most likely to be violated:**
1. Never publish Pub/Sub events inside a database transaction — use the Outbox pattern
2. Wrong tenant = 404 (not 403) — never reveal cross-tenant entity existence

---

## Phase 0 Exit Criteria

Before Phase 1 begins, all of these must be verified:

- [ ] All 5 services running in Cloud Run dev (green-pm-sandbox)
- [ ] RLS isolation: 2 tenants, zero cross-tenant data leakage across all tables
- [ ] PIG: `activity_created` → `graph_node` present within 5 seconds (P99)
- [ ] API Gateway: JWT auth passing for valid tokens, rejecting forged tokens
- [ ] Activity Workspace: `GET /workspaces/activities/{id}` returns full PIG-connected data
- [ ] Outbox: 100 events published, 0 lost, 0 duplicates (idempotency verified)
- [ ] Load baseline: PIG query P99 < 800ms at 50 concurrent users

---

## v1 Demo (Legacy)

The original demo (Evidence Score + Confidence Score, Northgate CCGT project, 40 activities) is preserved on `main`. See the [v1 README section](#v1-demo-setup) below if needed.

<details>
<summary>v1 Demo Setup</summary>

```bash
git checkout main
echo "ANTHROPIC_API_KEY=..." > .env
docker compose up --build -d db backend
docker compose run --rm seed
docker compose up -d frontend
# → http://localhost:3000
```

</details>
