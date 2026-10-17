# Implementation plan

Source: AGENTS.md and DEVELOPMENT_PLAN_KO.md. Only this independent repository is in scope.

Initial gaps: ephemeral global incident dictionary, caller-supplied tenant, no authentication,
database, approval, tablet, gateway, reports or integration tests.

Reviewable stages:
1. PostgreSQL/Alembic, opaque bearer credentials, factory-scoped RBAC, immutable approval and audit.
2. Korean tablet PWA with IndexedDB queue, explicit retry/conflicts and isolated login sessions.
3. Read-only Modbus TCP/RTU adapter, persistent edge outbox, idempotent authenticated ingest.
4. Approved evidence retrieval with citations; deterministic retrieval PoC, no unsupported LLM claims.
5. Daily/monthly exports, baseline-adjusted energy estimate, CI and operations documentation.

Cloud shell Git/proxy and package downloads currently fail. GitHub connector is available.
Source is reconstructed at commit 9d6da41e8071995839f7974a520a0a5de1bc5cd6;
remote commits will use that ancestry on a development branch. PostgreSQL integration
must run in GitHub CI or a provisioned environment; syntax checks alone are not acceptance.
No external ERP/MES writes, production deployment or machine control.

Later field work: real meter register maps, ESP32 firmware and hardware qualification,
10–20 site forms, photo/audio object storage, model evaluation and carbon passport approval.
