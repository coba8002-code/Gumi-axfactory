import io
from datetime import date, datetime
from typing import Literal
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import Response
from pydantic import Field
from .main import Input,principal,require,scope,audit
from .db import connect
from .analytics import period_bounds,downtime_minutes,energy_summary,production_adjusted

router=APIRouter()


class ReportIn(Input):
    period: Literal["daily","monthly"]
    day: date
    sensor_id: UUID | None = None


class BaselineIn(Input):
    baseline_kwh: float = Field(ge=0,allow_inf_nan=False)
    baseline_units: float = Field(gt=0,allow_inf_nan=False)
    actual_kwh: float = Field(ge=0,allow_inf_nan=False)
    actual_units: float = Field(gt=0,allow_inf_nan=False)
    source_evidence: str = Field(min_length=1,max_length=2000)
    comparable_product: str = Field(min_length=1,max_length=100)
    model_version: Literal["production-ratio-v1"]="production-ratio-v1"


@router.get("/sensors")
def sensors(user=Depends(principal)):
    require(user,"admin","supervisor")
    with connect() as db:
        return db.execute("SELECT id,equipment_id,name FROM sensors WHERE tenant_id=%s AND factory_id=%s",scope(user)).fetchall()


@router.post("/reports",status_code=201)
def generate(body:ReportIn,user=Depends(principal)):
    require(user,"admin","supervisor")
    try: start,end=period_bounds(body.day,body.period)
    except ValueError as e: raise HTTPException(422,str(e))
    if end>datetime.now(ZoneInfo("Asia/Seoul")):
        raise HTTPException(422,"완료된 일·월만 보고서로 확정할 수 있습니다")
    from psycopg.types.json import Jsonb
    with connect() as db:
        if body.sensor_id and not db.execute("SELECT id FROM sensors WHERE tenant_id=%s AND factory_id=%s AND id=%s",
                                            (*scope(user),body.sensor_id)).fetchone():
            raise HTTPException(404,"센서를 찾을 수 없습니다")
        old=db.execute("SELECT * FROM reports WHERE tenant_id=%s AND factory_id=%s AND period=%s AND day=%s AND sensor_id IS NOT DISTINCT FROM %s",
                       (*scope(user),body.period,body.day,body.sensor_id)).fetchone()
        if old:return old
        incidents=db.execute("""SELECT * FROM incidents WHERE tenant_id=%s AND factory_id=%s AND started_at<%s
            AND (ended_at IS NULL OR ended_at>%s)""",(*scope(user),end,start)).fetchall()
        readings=[]
        if body.sensor_id:
            readings=db.execute("""SELECT * FROM readings WHERE tenant_id=%s AND factory_id=%s AND sensor_id=%s
                AND metric='energy_kwh_interval' AND observed_at>%s
                AND observed_at-interval_seconds*interval '1 second'<%s ORDER BY observed_at""",
                (*scope(user),body.sensor_id,start,end)).fetchall()
        document=dict(period=body.period,day=str(body.day),timezone="Asia/Seoul",start=start.isoformat(),end=end.isoformat(),
            incident_count=len(incidents),approved_count=sum(x["approved"] for x in incidents),
            equipment_downtime_minutes=downtime_minutes(incidents,start,end),
            open_incidents=sum(x["ended_at"] is None for x in incidents),
            energy=energy_summary(readings,start,end) if body.sensor_id else None,
            source_incident_ids=[str(x["id"]) for x in incidents],source_reading_ids=[x["id"] for x in readings],
            limitations=["Snapshot as of generation time; late-arriving data is not included.",
                         "Downtime is equipment-minutes, overlaps merged per equipment; open events clipped at period end.",
                         "Not a verified savings or emissions certificate."],version="report-v1")
        row=db.execute("""INSERT INTO reports(id,tenant_id,factory_id,period,day,sensor_id,document)
            VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING RETURNING *""",
            (uuid4(),*scope(user),body.period,body.day,body.sensor_id,Jsonb(document))).fetchone()
        if not row:
            return db.execute("SELECT * FROM reports WHERE tenant_id=%s AND factory_id=%s AND period=%s AND day=%s AND sensor_id IS NOT DISTINCT FROM %s",
                              (*scope(user),body.period,body.day,body.sensor_id)).fetchone()
        audit(db,user,"report.generated",row["id"])
        return row


@router.get("/reports")
def list_reports(user=Depends(principal)):
    require(user,"admin","supervisor")
    with connect() as db:
        return db.execute("SELECT id,period,day,sensor_id,created_at FROM reports WHERE tenant_id=%s AND factory_id=%s ORDER BY created_at DESC LIMIT 100",scope(user)).fetchall()


def get_report(report_id,user):
    require(user,"admin","supervisor")
    with connect() as db:
        row=db.execute("SELECT * FROM reports WHERE tenant_id=%s AND factory_id=%s AND id=%s",(*scope(user),report_id)).fetchone()
        if not row:raise HTTPException(404,"보고서를 찾을 수 없습니다")
        return row


@router.get("/reports/{report_id}")
def report(report_id:UUID,user=Depends(principal)):
    return get_report(report_id,user)


@router.get("/reports/{report_id}/export")
def export(report_id:UUID,format:Literal["xlsx","pdf"]="xlsx",user=Depends(principal)):
    doc=get_report(report_id,user)["document"]
    fields=[("Period",doc["period"]),("Day (Asia/Seoul)",doc["day"]),("Incident count",doc["incident_count"]),
            ("Approved cases",doc["approved_count"]),("Equipment downtime minutes",doc["equipment_downtime_minutes"]),
            ("Open incidents",doc["open_incidents"])]
    if doc["energy"]:
        fields += [(k,v) for k,v in doc["energy"].items() if k!="limitations"]
    output=io.BytesIO()
    limits=doc["limitations"]+(doc["energy"]["limitations"] if doc["energy"] else ["No energy meter selected."])
    if format=="xlsx":
        from openpyxl import Workbook
        wb=Workbook();ws=wb.active;ws.title="Factory report"
        ws.append(["JUX Factory Intelligence","report-v1"])
        for label,value in fields:ws.append([label,value])
        for note in limits:ws.append(["Limitation",note])
        evidence=wb.create_sheet("Evidence")
        for key in ["source_incident_ids","source_reading_ids"]:
            for value in doc[key]:evidence.append([key,value])
        ws.column_dimensions["A"].width=34;ws.column_dimensions["B"].width=100
        wb.save(output);mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        from reportlab.pdfgen.canvas import Canvas
        from textwrap import wrap
        canvas=Canvas(output);y=800
        canvas.setFont("Helvetica",12);canvas.drawString(40,y,"JUX Factory Intelligence - pilot report");y-=30
        for label,value in fields:
            canvas.drawString(40,y,f"{label}: {value}");y-=20
        canvas.setFont("Helvetica",9)
        for note in limits:
            for line in wrap(note,100):
                canvas.drawString(40,y,line);y-=14
        canvas.drawString(40,y-20,"Evidence IDs are retained in the API snapshot and XLSX evidence sheet.")
        canvas.save();mime="application/pdf"
    return Response(output.getvalue(),media_type=mime,headers={"Content-Disposition":f'attachment; filename="factory-{doc["day"]}.{format}"'})


@router.post("/energy/assessments",status_code=201)
def assess(body:BaselineIn,user=Depends(principal)):
    require(user,"admin")
    result=production_adjusted(body.baseline_kwh,body.baseline_units,body.actual_kwh,body.actual_units)
    from psycopg.types.json import Jsonb
    with connect() as db:
        key=uuid4()
        db.execute("INSERT INTO energy_assessments(id,tenant_id,factory_id,actor_id,inputs,result) VALUES (%s,%s,%s,%s,%s,%s)",
                   (key,*scope(user),user["id"],Jsonb(body.model_dump()),Jsonb(result)))
        audit(db,user,"energy.estimate_created",key)
    return {"id":key,**result}
