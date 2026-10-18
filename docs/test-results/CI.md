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

## Final verified code

Commit: e01744aacdf186a07e5f0d55ba02fa1b793ed965.
[Full successful CI run 39047554430](https://github.com/coba8002-code/Gumi-axfactory/actions/runs/39047554430).

- PostgreSQL 16: all migrations and 15 backend/domain/integration tests passed, no skips.
- Gateway: 4 tests passed.
- Browser queue: 3 Node tests passed.
- Chromium: login, IndexedDB offline save, offline reload, reconnect sync and logout passed.
- pip-audit: dependency audit passed.
- Browser screenshot is retained as the run's tablet-preview artifact.

The browser test exposed a refresh failure that prevented restoring the queue; the final
code restores cached equipment and offline records even when network refresh fails.
The later dependency-audit change uses pinned FastAPI 0.141.1, Uvicorn 0.52.1 and Pydantic 2.13.4.

This confirms software pilot tests, not real-meter accuracy, ESP32 commissioning,
Docker Compose deployment, production security acceptance or verified energy savings.
The retrieval-only knowledge PoC has no LLM/embedding integration. Existing external JUX ERP/MES was not modified.
