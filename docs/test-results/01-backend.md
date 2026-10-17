# Stage 1 — PostgreSQL foundation

- Local Python compile: passed.
- Local API integration: 3 tests skipped because PostgreSQL/driver are unavailable.
- No database acceptance claim. CI provisions PostgreSQL 16 and applies Alembic before tests.
- Covers authentication, tenant/factory isolation, role denial, retry conflict,
  approval separation, durable read through a new connection, and audit visibility.
- Environment blockers: shell proxy connection refused, package installation unavailable,
  Docker socket operation not permitted.
