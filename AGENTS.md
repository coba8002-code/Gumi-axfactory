# Codex instructions — Gumi AX Factory

You are implementing an independent JUX Factory Intelligence product. Do not modify external JUX ERP/MES repositories.

## Mission
Build a production-oriented factory tablet + IoT + knowledge capture platform for Gumi smart industrial parks. Prioritize reliability, safety, Korean factory operator usability, tenant isolation, and evidence-backed energy savings.

## Work sequence
1. Inspect repository, document gaps, create short plan.
2. Establish backend FastAPI + PostgreSQL/Alembic, tenant-aware RBAC, audit log, API validation, unit/integration tests.
3. Build tablet PWA: equipment list, downtime events, reason codes, corrective action, photo/voice metadata, offline queue and retry.
4. Build gateway simulator + Modbus ingestion adapters, idempotency, event timestamps, sensor quality flags. No direct machine control.
5. Implement knowledge workflow: incident -> diagnosis hypotheses -> worker action -> reviewer approval -> searchable evidence. Use RAG with citations, never automatically treat worker notes as verified truths.
6. Implement daily/monthly reports with export and baseline-adjusted energy analysis; label estimates and measurement limitations.
7. Evaluate DeepSeek Harness separately (developer preview) using pinned versions and security review before integration. Do not execute arbitrary third-party plugins in production.
8. Add CI, security checks, Docker Compose, documentation, tests. Record results and limitations.

## Engineering constraints
- Python 3.12+, FastAPI, PostgreSQL; frontend React + TypeScript PWA recommended.
- Tenant-scoped access checks at database/query boundary, not only frontend.
- Credentials from environment only; no hard-coded keys or secrets.
- Raw factory data belongs to tenant; no cross-tenant AI retrieval.
- Never control industrial equipment directly without explicit safety design and site authorization.
- Do not fabricate real-world savings or failure predictions.
- Commit in reviewable increments. Tests must pass before claiming completion.
- Ask only when blocked by an external permission or irreversible decision.

## Acceptance criteria (MVP)
A worker can select equipment, record downtime reason and corrective action, supervisor can approve a case, and admin can see per-factory reports. Data survives restart and is isolated by tenant. Sensor events can be ingested idempotently; reports distinguish measured from estimated values.
