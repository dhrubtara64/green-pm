# Green PM — Demo Version

Evidence-backed engineering project intelligence for EPC firms.
Reads from your existing schedule, documents, and BOQ — never replaces them.

---

## Quick start (two commands)

```bash
# 1. Add your Anthropic API key
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env

# 2. Start the database and backend
docker-compose up --build -d db backend

# 3. Seed the demo project (Northgate CCGT — wait ~5s for postgres to be ready)
docker-compose run --rm seed

# 4. Start the frontend
docker-compose up -d frontend
```

Then open **http://localhost:3000**.

That's it. The demo project (Northgate CCGT Power Plant, 40 activities) is pre-loaded.

---

## What's running

| Service | URL | Description |
|---------|-----|-------------|
| Frontend | http://localhost:3000 | Next.js dashboard |
| Backend API | http://localhost:8000 | FastAPI + Python |
| API Docs | http://localhost:8000/docs | Swagger UI |
| Database | localhost:5432 | PostgreSQL |

---

## Demo walkthrough (follows `client_demo_plan.md` narrative)

### Step 1 — Show the coexistence statement
Open the dashboard. Point out: "This is sourced from the project's own P6 schedule and document folder — it doesn't replace Primavera."

### Step 2 — Show the Progress Confidence view
The dashboard lists all 40 activities. Key moments:
- **HRSG Drum Installation** (WBS 2.4, Mechanical) — Evidence Score: 80%, Confidence: 35%. Three sources agree, but all from Thermax, a vendor with a history of overclaiming. This is the **key divergence moment** — show that a high Evidence Score does not automatically mean high Confidence.
- **MCC Room Cabling** (WBS 4.3, Electrical) — flagged "Verification Required" due to contradicting QC inspection.
- **GT Foundation Concrete Pour** (WBS 1.3, Civil) — Evidence: 20%, Confidence: 30%. Single stale source from 4 weeks ago.
- **HP Steam Hydro Test** (WBS 3.3, Piping) — Evidence: 30%, Confidence: 75%. Single source, but a Bureau Veritas certified test — high reliability from one source.

### Step 3 — Click into the evidence trail
Click on **HRSG Drum Installation**. Show:
- Three evidence items (Thermax progress report, site photos, P6 schedule entry)
- All marked "Low" or "Medium" source reliability
- The AI reasoning explaining why Confidence is lower than Evidence Score

### Step 4 — Show confirm/correct live
Click on **MCC Room Cabling**. Show:
- The contradicting evidence (Electrical weekly report: 55% vs QC inspection: 30-35%)
- Click "Correct" on Reported Progress → change from 55 to 35
- Click "Apply Correction" — scores recompute, the dashboard updates

### Step 5 — Show the weekly report
Go to **Weekly Report** → "Generate New Draft". The report is pre-drafted from current activity evidence. Edit a line, then click "Send →" (logs the action — no real email sent). Show the "Send action logged" confirmation.

### Step 6 — Green PM AI chat
Back on any activity page, click "Green PM AI" (top right). Try:
- "Why is this activity's confidence score low?"
- "What evidence supports the reported progress?"
- "What's missing for this activity?"

The chat is scoped to this one activity — it won't answer project-wide questions.

---

## Loading a real prospect schedule (before a specific pitch)

```bash
# Use the API directly — same code path as seed data
curl -X POST http://localhost:8000/ingest/schedule \
  -F "file=@/path/to/prospect_project.xer"

# Then recompute all scores
curl -X POST http://localhost:8000/ingest/recompute-all
```

Supported formats: P6 XER, MS Project XML.

---

## Development (no Docker)

```bash
# Backend
cd backend
pip install -r requirements.txt
createdb greenpm
DATABASE_URL=postgresql://localhost/greenpm python seed/generate_seed_data.py
DATABASE_URL=postgresql://localhost/greenpm uvicorn app.main:app --reload

# Frontend (separate terminal)
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

---

## Architecture decisions logged (for Product Council review)

| Decision | Choice | Why |
|----------|--------|-----|
| Evidence Score formula | `(count/5 × 0.35) + (recency × 0.35) + (corroboration × 0.30)` | Deterministic, no LLM, saturates at 5 sources, decays over 30 days |
| Confidence Score | LLM-calibrated via Anthropic `claude-sonnet-4-6` | Weighs source reliability + correction history beyond raw evidence count |
| Score recompute trigger | On-demand (ingest endpoint + API button) | Event-driven; polling would be wasteful at V1 scale |
| P6 parser | Custom XER tab-delimited parser + XML fallback | Covers 95% of real P6 exports without extra dependencies |
| source_reliability_signal | Enum: high/medium/low/unverified | Heuristic at ingestion time; feeds Confidence Score, not Evidence Score |
| "Verification Required" | evidence_score < 0.25 AND confidence_score < 0.30, OR contradicting EvidenceItem | Conservative — only flags when both thin AND contradicted |
| Relationships | Explicit join tables with `relation_type` column | Graph-migration-ready; no JSON blobs |
| Report "Send" | Logged no-op | V1: no outbound integration; audit trail preserved for V2 |

---

## What's out of scope (V1)

- Tier 2–4 ingestion (no Procore/Aconex API)
- Risk Agent, Change/Dependency Agent, Commercial Agent
- Computer vision, drone, IoT
- Multi-tenant auth / billing
- Real outbound email
- Open-ended project-wide chat (chat is scoped to one activity)
- Graph database (Postgres only; ready to migrate to Neo4j in V2)
