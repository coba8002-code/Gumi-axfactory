# Gumi AX Factory — JUX Factory Intelligence

구미 스마트산단 에너지·설비·현장업무·암묵지 AI 통합 플랫폼의 독립 개발 저장소.

## MVP scope
- 작업자 태블릿: 설비 선택, 정지 사유, 정비 조치, 음성/사진 기록(후속)
- 설비 데이터: 전력·상태·알람 수집 (초기에는 시뮬레이터)
- 암묵지: 현장 해결사례 등록·검증·검색 (RAG 연동 후속)
- 관리자: 작업일지·정지시간·전력량 보고서
- 공장/사용자별 데이터 격리, 감사기록 및 안전한 운영

## Implemented pilot

- PostgreSQL 16 + Alembic persistence, scoped bearer identities, worker/supervisor/admin/device RBAC.
- Korean tablet PWA with durable IndexedDB queue and retry, separate reviewer approval, append-only audit.
- Dedicated PC monitoring/admin site at /management/: sensor trends, freshness/quality, approval, inventory, reports, account revocation and audit.
- Sensor/device registration, idempotent ingestion with unit/quality/provenance checks, read-only Modbus PC reference.
- Approved-case retrieval with citations (retrieval PoC; no external LLM/embedding integration).
- Immutable daily/monthly report snapshots, XLSX/PDF export, scheduled generation and labeled energy estimates.

Start the full stack via [OPERATIONS.md](docs/OPERATIONS.md). The app is available on
http://localhost:8080 after configuring environment credentials and provisioning identities.

## Local API quickstart
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# Configure DATABASE_URL with your PostgreSQL connection first.
alembic upgrade head
uvicorn app.main:app --reload
```
Windows: `.venv\Scripts\activate`.
API docs: http://localhost:8000/docs

## Status
독립 파일럿 MVP입니다. 단계별 결과는 [docs/test-results](docs/test-results)에 기록합니다.
실장비·ESP32 펌웨어, 사진/음성 업로드, 의미 기반 RAG·LLM, 검증된 에너지 절감,
탄소 패스포트, 현장 보안·백업복구 인수는 후속 과제입니다.
DeepSeek Harness 및 외부 JUX ERP·MES와 연결하거나 운영 배포하지 않았습니다.

See [AGENTS.md](AGENTS.md) for Codex tasks and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for design.

