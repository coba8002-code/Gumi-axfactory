# Control room / management site

New separate /management/ entry point: overview, sensors/equipment, approval,
approved knowledge, reports, accounts and append-only audit viewer.

Local JavaScript syntax and existing queue checks passed. Domain tests passed;
11 PostgreSQL tests skipped locally because DB access is unavailable. CI includes:

- Same-tenant/factory scope, worker/device monitoring denial, stale data, bounded series retrieval.
- No credential hashes in identity lists; supervisor denial and cross-factory revocation denial.
- Self-deactivation prevention and effective access revocation.
- Real browser responsive overview/chart, equipment registration, approval dialog,
  account revocation, navigation and worker access denial.

Control room freshness is not equipment operational status. No industrial control introduced.
Standalone preview uses explicitly labeled sample data. Final CI evidence follows after execution.
