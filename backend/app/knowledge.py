"""Evidence-only retrieval PoC. No LLM call, autonomous diagnosis or training."""
from fastapi import APIRouter, Depends, Query
from .main import principal, require, scope
from .db import connect

router=APIRouter()


def literal_pattern(query):
    return "%" + query.replace("\\","\\\\").replace("%","\\%").replace("_","\\_") + "%"


@router.get("/knowledge")
def knowledge(q: str = Query(min_length=2,max_length=200), user=Depends(principal)):
    require(user,"worker","supervisor","admin")
    with connect() as db:
        rows=db.execute("""
            SELECT i.id,i.equipment_id,i.notes,i.evidence,i.approved_at,
                   string_agg(a.action || ' → ' || a.outcome, E'\n' ORDER BY a.created_at) AS actions
            FROM incidents i JOIN corrective_actions a
              ON a.tenant_id=i.tenant_id AND a.factory_id=i.factory_id AND a.incident_id=i.id
            WHERE i.tenant_id=%s AND i.factory_id=%s AND i.approved=true
            GROUP BY i.id
            HAVING (i.notes || ' ' || i.evidence || ' ' || string_agg(a.action || ' ' || a.outcome,' ')) ILIKE %s
            ORDER BY i.approved_at DESC LIMIT 10
        """,(*scope(user),literal_pattern(q))).fetchall()
    return {
        "mode":"approved-evidence-retrieval-v1",
        "answer":"승인된 사례의 조치·결과를 확인하세요. 현재 설비의 진단은 담당자가 검토해야 합니다."
                 if rows else "해당 공장에 일치하는 승인 근거가 없습니다.",
        "sources":[{**r,"citation":"/incidents/"+str(r["id"]),"trust":"supervisor-approved"} for r in rows],
        "limitations":["문자열 검색 PoC; 의미 기반 임베딩·생성형 답변은 아직 연결하지 않았습니다.",
                        "사례 내용은 과거 작업 증빙이며 현재 설비에 대한 확정 진단이 아닙니다."]
    }
