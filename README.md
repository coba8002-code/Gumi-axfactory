# Gumi AX Factory — JUX Factory Intelligence

구미 스마트산단 에너지·설비·현장업무·암묵지 AI 통합 플랫폼의 독립 개발 저장소.

## MVP scope
- 작업자 태블릿: 설비 선택, 정지 사유, 정비 조치, 음성/사진 기록(후속)
- 설비 데이터: 전력·상태·알람 수집 (초기에는 시뮬레이터)
- 암묵지: 현장 해결사례 등록·검증·검색 (RAG 연동 후속)
- 관리자: 작업일지·정지시간·전력량 보고서
- 공장/사용자별 데이터 격리, 감사기록 및 안전한 운영

## Local API quickstart
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Windows: `.venv\Scripts\activate`.
API docs: http://localhost:8000/docs

## Status
초기 API 스캐폴드. 개발용 인메모리 저장소이며 실공장 운영 금지. 인증, PostgreSQL, 장비 연결, 자동 보고서, DeepSeek Harness는 후속 구현 필요.

See [AGENTS.md](AGENTS.md) for Codex tasks and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for design.

