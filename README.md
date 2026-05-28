# Breathe ESG

A prototype platform for ingesting and reviewing corporate emissions activity data. It accepts file exports from SAP, utility portals, and travel management platforms, normalizes them into a structured record store, and surfaces them for analyst review.

## Local Development

```bash
# 1. Clone
git clone <repo-url>
cd breathe_esg

# 2. Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Database
python manage.py migrate
python manage.py seed_demo

# 4. Run backend
python manage.py runserver

# 5. Frontend (separate terminal)
cd ../frontend
npm install
npm run dev
```

The backend runs at `http://localhost:8000`. The frontend dev server runs at `http://localhost:5173` and proxies API requests to the backend.

## Demo Credentials

Username: `analyst`
Password: `demo1234`

## Live URL

See Railway deployment — URL TBD.

## Repo Structure

```
backend/          Django REST API — models, ingestion pipeline, review endpoints
frontend/         React app — file upload, record review table, status dashboard
MODEL.md          Data model decisions and rationale
DECISIONS.md      Integration and architecture decisions
TRADEOFFS.md      Deliberate non-builds and what production would need
SOURCES.md        Data source research, sample data notes, production gaps
```

## Design Documents

- [MODEL.md](./MODEL.md) — UUID PKs, immutable RawRecord, multi-tenancy, scope classification, unit normalization, audit trail
- [DECISIONS.md](./DECISIONS.md) — SAP flat file vs IDoc/OData, ME2M vs FI, utility CSV vs PDF/Green Button, travel CSV vs Concur API, file upload vs API pull, no Celery, no emission factors, token auth
- [TRADEOFFS.md](./TRADEOFFS.md) — Async processing, emission factor computation, cross-run duplicate detection
- [SOURCES.md](./SOURCES.md) — SAP, utility, and travel source format research and production gap analysis
