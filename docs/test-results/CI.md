# CI evidence

| Stage | Commit | Run | Result |
|---|---|---|---|
| PostgreSQL foundation | e5d147a | [39046698872](https://github.com/coba8002-code/Gumi-axfactory/actions/runs/39046698872) | Passed PostgreSQL migration and API tests |
| Tablet source | c971d3f | [39046849464](https://github.com/coba8002-code/Gumi-axfactory/actions/runs/39046849464) | Backend CI passed; queue tests ran locally |
| IoT source | a2247dd | [39046852752](https://github.com/coba8002-code/Gumi-axfactory/actions/runs/39046852752) | Backend/domain CI passed; gateway tests ran locally |
| Approved knowledge | 760d0a8 | [39046910905](https://github.com/coba8002-code/Gumi-axfactory/actions/runs/39046910905) | Approval/citation isolation tests passed |
| Full report stage | 45113fa | [39047246280](https://github.com/coba8002-code/Gumi-axfactory/actions/runs/39047246280) | PostgreSQL/backend 14, edge 4, queue 3 passed; browser setup failed |

The report-stage failure was an invalid Python Playwright package version (1.51.1).
Corrected to the available pinned 1.62.0; browser test and final CI will be re-run.
No skipped local PostgreSQL test is counted as a pass.
