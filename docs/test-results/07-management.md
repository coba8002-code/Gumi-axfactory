# Control room / management site

New separate /management/ entry point: overview, sensors/equipment, approval,
approved knowledge, reports, accounts and append-only audit viewer.

Verified code commit: b38a32866ca535b10b9910455fb8026baf2682ab
CI: https://github.com/coba8002-code/Gumi-axfactory/actions/runs/39093648524
Result: SUCCESS (backend and dependency-audit jobs), 2026-10-18 UTC.

- Backend: 18 tests passed with PostgreSQL 16, including factory isolation,
  worker/device monitoring denial, stale readings and bounded series retrieval.
- Identity checks: credential hashes omitted; supervisor and cross-factory denial;
  self-deactivation prevention and effective access revocation passed.
- Edge gateway: 4 tests passed. Offline queue: 3 tests passed.
- Chromium tablet: login, IndexedDB offline save/reload, reconnect sync and logout passed.
- Chromium management: chart, responsive 1440/390 layouts, equipment registration,
  approval dialog, account revocation, navigation and worker denial passed.
- Dependency audit passed. Screenshots are retained in the CI tablet-preview artifact.

Local JavaScript syntax and queue checks passed. Local backend execution skipped
11 PostgreSQL tests because DB access was unavailable; CI ran all 18 without skips.

Control room freshness is not equipment operational status. No industrial control introduced.
Standalone preview uses explicitly labeled sample data. No physical-device or production
integration validation is claimed. Existing external JUX ERP/MES was not modified.
