import hashlib
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID, uuid4
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, ConfigDict, Field, AwareDatetime, model_validator
from .db import connect

app = FastAPI(title="JUX Factory Intelligence", version="0.2.0")
bearer = HTTPBearer(auto_error=False)


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


def principal(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
    if not credentials:
        raise HTTPException(401, "인증이 필요합니다")
    with connect() as db:
        user = db.execute("SELECT id,tenant_id,factory_id,role FROM identities WHERE token_hash=%s AND active",
                          (hashlib.sha256(credentials.credentials.encode()).hexdigest(),)).fetchone()
    if not user:
        raise HTTPException(401, "인증이 유효하지 않습니다")
    return user


def require(user, *roles):
    if user["role"] not in roles:
        raise HTTPException(403, "권한이 없습니다")


def scope(user):
    return user["tenant_id"], user["factory_id"]


def audit(db, user, action, entity):
    db.execute("INSERT INTO audit_events(tenant_id,factory_id,actor_id,action,entity_id) VALUES (%s,%s,%s,%s,%s)",
               (*scope(user), user["id"], action, str(entity)))


def incident(db, user, item_id, lock=False):
    row = db.execute("SELECT * FROM incidents WHERE tenant_id=%s AND factory_id=%s AND id=%s"
                     + (" FOR UPDATE" if lock else ""), (*scope(user), item_id)).fetchone()
    if not row:
        raise HTTPException(404, "기록을 찾을 수 없습니다")
    return row


class EquipmentIn(Input):
    name: str = Field(min_length=1, max_length=100)


class IncidentIn(Input):
    id: UUID = Field(default_factory=uuid4)
    equipment_id: UUID
    reason: Literal["fault", "tool", "material", "setup", "other"]
    notes: str = Field(default="", max_length=4000)
    started_at: AwareDatetime
    ended_at: AwareDatetime | None = None

    @model_validator(mode="after")
    def times(self):
        now = datetime.now(timezone.utc)
        if self.started_at > now or (self.ended_at and not self.started_at <= self.ended_at <= now):
            raise ValueError("시작·종료 시각을 확인하세요")
        return self


class ActionIn(Input):
    id: UUID = Field(default_factory=uuid4)
    action: str = Field(min_length=1, max_length=4000)
    outcome: str = Field(min_length=1, max_length=4000)


class ApprovalIn(Input):
    resolved: bool
    evidence: str = Field(min_length=1, max_length=4000)
    ended_at: AwareDatetime


@app.get("/health")
def health():
    return {"status": "ok", "mode": "pilot"}


@app.get("/ready")
def ready():
    with connect() as db:
        db.execute("SELECT 1 FROM alembic_version").fetchone()
    return {"status": "ready"}


@app.get("/me")
def me(user=Depends(principal)):
    return user


@app.get("/equipment")
def equipment(user=Depends(principal)):
    require(user, "worker", "supervisor", "admin")
    with connect() as db:
        return db.execute("SELECT * FROM equipment WHERE tenant_id=%s AND factory_id=%s ORDER BY name", scope(user)).fetchall()


@app.post("/equipment", status_code=201)
def create_equipment(body: EquipmentIn, user=Depends(principal)):
    require(user, "admin")
    with connect() as db:
        row = db.execute("INSERT INTO equipment(id,tenant_id,factory_id,name) VALUES (%s,%s,%s,%s) RETURNING *",
                         (uuid4(), *scope(user), body.name)).fetchone()
        audit(db, user, "equipment.created", row["id"])
        return row


@app.post("/incidents", status_code=201)
def create_incident(body: IncidentIn, user=Depends(principal)):
    require(user, "worker", "supervisor", "admin")
    with connect() as db:
        if not db.execute("SELECT id FROM equipment WHERE tenant_id=%s AND factory_id=%s AND id=%s",
                          (*scope(user), body.equipment_id)).fetchone():
            raise HTTPException(404, "설비를 찾을 수 없습니다")
        row = db.execute("""INSERT INTO incidents
            (id,tenant_id,factory_id,equipment_id,created_by,reason,notes,started_at,ended_at,original_ended_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING RETURNING *""",
            (body.id, *scope(user), body.equipment_id, user["id"], body.reason, body.notes,
             body.started_at, body.ended_at, body.ended_at)).fetchone()
        if not row:
            row = incident(db, user, body.id)
            expected = dict(equipment_id=body.equipment_id, created_by=user["id"], reason=body.reason,
                            notes=body.notes, started_at=body.started_at, original_ended_at=body.ended_at)
            if any(row[k] != v for k, v in expected.items()):
                raise HTTPException(409, "중복 키 내용 충돌")
            return row
        audit(db, user, "incident.created", row["id"])
        return row


@app.get("/incidents")
def list_incidents(user=Depends(principal)):
    require(user, "worker", "supervisor", "admin")
    with connect() as db:
        return db.execute("SELECT * FROM incidents WHERE tenant_id=%s AND factory_id=%s ORDER BY started_at DESC LIMIT 200",
                          scope(user)).fetchall()


@app.get("/incidents/{item_id}")
def get_incident(item_id: UUID, user=Depends(principal)):
    require(user, "worker", "supervisor", "admin")
    with connect() as db:
        row = incident(db, user, item_id)
        row["actions"] = db.execute("SELECT * FROM corrective_actions WHERE tenant_id=%s AND factory_id=%s AND incident_id=%s ORDER BY created_at",
                                   (*scope(user), item_id)).fetchall()
        return row


@app.post("/incidents/{item_id}/actions")
def add_action(item_id: UUID, body: ActionIn, user=Depends(principal)):
    require(user, "worker", "supervisor", "admin")
    with connect() as db:
        row = incident(db, user, item_id, lock=True)
        old = db.execute("SELECT * FROM corrective_actions WHERE tenant_id=%s AND factory_id=%s AND id=%s",
                         (*scope(user), body.id)).fetchone()
        if old:
            if any(old[k] != v for k,v in dict(incident_id=item_id,action=body.action,outcome=body.outcome,actor_id=user["id"]).items()):
                raise HTTPException(409, "중복 조치 키 충돌")
            return old
        if row["approved"]:
            raise HTTPException(409, "승인 기록은 변경할 수 없습니다")
        result = db.execute("""INSERT INTO corrective_actions(id,tenant_id,factory_id,incident_id,actor_id,action,outcome)
            VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING *""",
            (body.id, *scope(user), item_id, user["id"], body.action, body.outcome)).fetchone()
        audit(db, user, "incident.action_added", item_id)
        return result


@app.post("/incidents/{item_id}/approve")
def approve(item_id: UUID, body: ApprovalIn, user=Depends(principal)):
    require(user, "supervisor", "admin")
    with connect() as db:
        row = incident(db, user, item_id, lock=True)
        if row["approved"]:
            raise HTTPException(409, "이미 승인되었습니다")
        actions = db.execute("SELECT actor_id FROM corrective_actions WHERE tenant_id=%s AND factory_id=%s AND incident_id=%s",
                             (*scope(user), item_id)).fetchall()
        if not actions or not body.resolved:
            raise HTTPException(422, "조치와 해결 증빙이 필요합니다")
        if row["created_by"] == user["id"] or any(a["actor_id"] == user["id"] for a in actions):
            raise HTTPException(403, "작성·조치 담당자와 검토자는 달라야 합니다")
        if not row["started_at"] <= body.ended_at <= datetime.now(timezone.utc):
            raise HTTPException(422, "종료 시각을 확인하세요")
        result = db.execute("""UPDATE incidents SET approved=true,approved_by=%s,approved_at=now(),evidence=%s,ended_at=%s
            WHERE tenant_id=%s AND factory_id=%s AND id=%s RETURNING *""",
            (user["id"], body.evidence, body.ended_at, *scope(user), item_id)).fetchone()
        audit(db, user, "incident.approved", item_id)
        return result


@app.get("/audit")
def audit_log(user=Depends(principal)):
    require(user, "admin")
    with connect() as db:
        return db.execute("SELECT * FROM audit_events WHERE tenant_id=%s AND factory_id=%s ORDER BY id DESC LIMIT 200",
                          scope(user)).fetchall()


from .telemetry import router as telemetry_router
app.include_router(telemetry_router)
from .knowledge import router as knowledge_router
app.include_router(knowledge_router)
from .reports import router as reports_router
app.include_router(reports_router)
