# Stage 5 — reports and full verification

- Local analytics: 4 tests passed (Korean periods/leap year, downtime union/clipping,
  measured vs estimated coverage, negative savings).
- Backend local run: 7 unit tests passed, 7 PostgreSQL integration tests skipped.
- Browser execution locally blocked by socket PermissionError; Chromium test is in CI.
- Added actual PostgreSQL tests for ingestion retry/overlap, sensor identity, snapshots,
  report isolation and binary XLSX/PDF exports.
- Docker Compose authored, not run in the restricted local environment.
- CI evidence will be recorded after the complete-stage commit.
