"""Read-only control room and scoped administration; no equipment control."""
from datetime import datetime, timezone, timedelta
from typing import Literal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from .main import principal, require, scope, audit
from .db import connect

router = APIRouter()


@router.get("/monitoring")
def monitoring(user=Depends(principal)):
    require(user, "admin", "supervisor")
    now = datetime.now(timezone.utc)
    with connect() as db:
        # One consistent snapshot for counters and streams.
        db.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        equipment = db.execute("SELECT id,name FROM equipment WHERE tenant_id=%s AND factory_id=%s ORDER BY name",
                               scope(user)).fetchall()
        sensors = db.execute("""
          SELECT s.id,s.name,s.equipment_id,e.name AS equipment_name,r.observed_at,r.received_at,
                 r.metric,r.value,r.unit,r.quality,r.source
          FROM sensors s JOIN equipment e ON e.tenant_id=s.tenant_id AND e.factory_id=s.factory_id AND e.id=s.equipment_id
          LEFT JOIN LATERAL (
            SELECT observed_at,received_at,metric,value,unit,quality,source FROM readings
            WHERE tenant_id=s.tenant_id AND factory_id=s.factory_id AND sensor_id=s.id
            ORDER BY observed_at DESC,id DESC LIMIT 1
          ) r ON true
          WHERE s.tenant_id=%s AND s.factory_id=%s ORDER BY s.name
        """, scope(user)).fetchall()
        counts = db.execute("""SELECT count(*) FILTER(WHERE NOT approved) AS pending,
          count(*) FILTER(WHERE ended_at IS NULL) AS open
          FROM incidents WHERE tenant_id=%s AND factory_id=%s""",scope(user)).fetchone()
    for sensor in sensors:
        timestamp = sensor["observed_at"]
        sensor["stream_status"] = ("no_data" if timestamp is None else
            "attention" if sensor["quality"]=="bad" or timestamp < now-timedelta(minutes=5) or timestamp > now else "recent")
    return {"as_of":now,"equipment":equipment,"sensors":sensors,
            "summary":{"equipment":len(equipment),"sensors":len(sensors),
                       "recent_streams":sum(s["stream_status"]=="recent" for s in sensors),
                       "attention_streams":sum(s["stream_status"]!="recent" for s in sensors),
                       "pending_incidents":counts["pending"],"open_incidents":counts["open"]},
            "freshness_seconds":300,
            "limitations":["수집 상태는 계측 시각 기준이며 설비의 가동·정상 여부를 의미하지 않습니다.",
                           "시뮬레이터·추정·불량 데이터를 구분해 확인하세요."]}


@router.get("/monitoring/readings")
def series(sensor_id:UUID,metric:Literal["power_kw","energy_kwh_interval","temperature_c"]="power_kw",
           user=Depends(principal)):
    require(user,"admin","supervisor")
    with connect() as db:
        if not db.execute("SELECT id FROM sensors WHERE tenant_id=%s AND factory_id=%s AND id=%s",
                          (*scope(user),sensor_id)).fetchone():
            raise HTTPException(404,"센서를 찾을 수 없습니다")
        rows=db.execute("""SELECT id,observed_at,received_at,value,unit,quality,source FROM readings
          WHERE tenant_id=%s AND factory_id=%s AND sensor_id=%s AND metric=%s
          ORDER BY observed_at DESC,id DESC LIMIT 240""",(*scope(user),sensor_id,metric)).fetchall()
    return {"metric":metric,"points":list(reversed(rows)),"limit":240}


@router.get("/management/identities")
def identities(user=Depends(principal)):
    require(user,"admin")
    with connect() as db:
        return db.execute("SELECT id,role,active FROM identities WHERE tenant_id=%s AND factory_id=%s ORDER BY role,id",
                          scope(user)).fetchall()


@router.post("/management/identities/{identity_id}/deactivate")
def deactivate(identity_id:UUID,user=Depends(principal)):
    require(user,"admin")
    if identity_id==user["id"]:
        raise HTTPException(409,"현재 접속한 계정은 이 화면에서 중지할 수 없습니다")
    with connect() as db:
        row=db.execute("UPDATE identities SET active=false WHERE tenant_id=%s AND factory_id=%s AND id=%s RETURNING id,role,active",
                       (*scope(user),identity_id)).fetchone()
        if not row:raise HTTPException(404,"계정을 찾을 수 없습니다")
        audit(db,user,"identity.deactivated",identity_id)
        return row
