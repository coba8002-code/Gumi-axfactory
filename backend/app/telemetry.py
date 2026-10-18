import hashlib
import json
from datetime import datetime, timezone, timedelta
from typing import Literal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field, AwareDatetime, model_validator
from .main import Input, principal, require, scope, audit
from .db import connect

router = APIRouter()


class SensorIn(Input):
    id: UUID
    equipment_id: UUID
    device_id: UUID
    name: str = Field(min_length=1, max_length=100)


class ReadingIn(Input):
    sensor_id: UUID
    event_id: UUID
    observed_at: AwareDatetime
    metric: Literal["power_kw", "energy_kwh_interval", "temperature_c"]
    value: float = Field(allow_inf_nan=False)
    unit: Literal["kW", "kWh", "degC"]
    interval_seconds: int | None = Field(default=None, gt=0, le=86400)
    quality: Literal["good", "estimated", "bad"]
    source: Literal["simulator", "modbus_tcp", "modbus_rtu"]
    firmware_version: str = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def valid(self):
        units = {"power_kw":"kW","energy_kwh_interval":"kWh","temperature_c":"degC"}
        if units[self.metric] != self.unit:
            raise ValueError("metric/unit mismatch")
        if self.metric != "temperature_c" and self.value < 0:
            raise ValueError("negative power/energy")
        if self.metric == "energy_kwh_interval" and self.interval_seconds is None:
            raise ValueError("energy must be an interval delta, not a cumulative counter")
        if self.observed_at > datetime.now(timezone.utc) + timedelta(minutes=5):
            raise ValueError("device clock is in the future")
        self.observed_at = self.observed_at.astimezone(timezone.utc)
        return self


@router.post("/sensors", status_code=201)
def register_sensor(body: SensorIn, user=Depends(principal)):
    require(user, "admin")
    with connect() as db:
        for table, item_id in [("equipment",body.equipment_id),("identities",body.device_id)]:
            row = db.execute(f"SELECT * FROM {table} WHERE tenant_id=%s AND factory_id=%s AND id=%s",
                             (*scope(user), item_id)).fetchone()
            if not row or (table == "identities" and (row["role"] != "device" or not row["active"])):
                raise HTTPException(404, "설비 또는 장비 계정을 찾을 수 없습니다")
        row = db.execute("""INSERT INTO sensors(id,tenant_id,factory_id,equipment_id,device_id,name)
            VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING RETURNING *""",
            (body.id, *scope(user), body.equipment_id, body.device_id, body.name)).fetchone()
        if not row:
            raise HTTPException(409, "이미 등록된 센서 ID")
        audit(db,user,"sensor.registered",body.id)
        return row


@router.post("/readings", status_code=201)
def ingest(body: ReadingIn, user=Depends(principal)):
    require(user, "device")
    digest = hashlib.sha256(json.dumps(body.model_dump(mode="json"),sort_keys=True).encode()).hexdigest()
    with connect() as db:
        # Serialize the stream: retries, conflicting IDs and interval overlap are atomic.
        sensor = db.execute("SELECT * FROM sensors WHERE tenant_id=%s AND factory_id=%s AND id=%s AND device_id=%s FOR UPDATE",
                            (*scope(user),body.sensor_id,user["id"])).fetchone()
        if not sensor:
            raise HTTPException(404, "등록된 센서가 아닙니다")
        previous = db.execute("SELECT id,payload_hash FROM readings WHERE tenant_id=%s AND factory_id=%s AND sensor_id=%s AND event_id=%s",
                              (*scope(user),body.sensor_id,body.event_id)).fetchone()
        if previous:
            if previous["payload_hash"] != digest:
                raise HTTPException(409,"event_id payload conflict")
            return {"id":previous["id"],"duplicate":True}
        if body.metric == "energy_kwh_interval":
            start = body.observed_at-timedelta(seconds=body.interval_seconds)
            overlap = db.execute("""SELECT id FROM readings WHERE tenant_id=%s AND factory_id=%s AND sensor_id=%s
                AND metric='energy_kwh_interval' AND observed_at > %s
                AND observed_at - interval_seconds * interval '1 second' < %s LIMIT 1""",
                (*scope(user),body.sensor_id,start,body.observed_at)).fetchone()
            if overlap:
                raise HTTPException(409,"overlapping energy intervals")
        row = db.execute("""INSERT INTO readings
            (tenant_id,factory_id,sensor_id,event_id,observed_at,metric,value,unit,interval_seconds,quality,source,firmware_version,payload_hash)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
            (*scope(user),body.sensor_id,body.event_id,body.observed_at,body.metric,body.value,body.unit,
             body.interval_seconds,body.quality,body.source,body.firmware_version,digest)).fetchone()
        return {"id":row["id"],"duplicate":False}
