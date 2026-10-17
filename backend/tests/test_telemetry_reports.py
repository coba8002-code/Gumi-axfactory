from datetime import datetime, timezone, timedelta, date
from uuid import uuid4
import test_api as support


class TelemetryReportsTest(support.Fixture):
    def setUp(self):
        super().setUp()
        device_id=self.client.get("/me",headers=self.device).json()["id"]
        self.sensor=str(uuid4())
        response=self.client.post("/sensors",headers=self.admin,
            json=dict(id=self.sensor,equipment_id=self.eq,device_id=device_id,name="메인 전력계"))
        self.assertEqual(response.status_code,201,response.text)
        self.reading=dict(sensor_id=self.sensor,event_id=str(uuid4()),observed_at="2026-01-01T00:00:00Z",
            metric="energy_kwh_interval",value=10,unit="kWh",interval_seconds=3600,
            quality="good",source="modbus_tcp",firmware_version="test")

    def test_ingestion_idempotency_scope_and_overlap(self):
        for duplicate in [False,True]:
            r=self.client.post("/readings",headers=self.device,json=self.reading)
            self.assertEqual(r.status_code,201,r.text)
            self.assertEqual(r.json()["duplicate"],duplicate)
        self.assertEqual(self.client.post("/readings",headers=self.worker,json=self.reading).status_code,403)
        another_device=self.identity("device")
        self.assertEqual(self.client.post("/readings",headers=another_device,json=self.reading).status_code,404)
        for changes in [{"value":12},{"event_id":str(uuid4())}]:
            self.assertEqual(self.client.post("/readings",headers=self.device,json={**self.reading,**changes}).status_code,409)
        self.assertEqual(self.client.post("/readings",headers=self.device,json={**self.reading,"unit":"kW"}).status_code,422)

    def test_report_persistence_exports_and_no_tenant_leak(self):
        self.client.post("/readings",headers=self.device,json=self.reading)
        payload=dict(period="daily",day="2026-01-01",sensor_id=self.sensor)
        r=self.client.post("/reports",headers=self.admin,json=payload)
        self.assertEqual(r.status_code,201,r.text)
        report=r.json();key=report["id"]
        self.assertEqual(report["document"]["energy"]["measured_kwh"],10)
        self.assertEqual(self.client.post("/reports",headers=self.admin,json=payload).json()["id"],key)
        for outsider in [self.other,self.other_factory]:
            self.assertEqual(self.client.get("/reports/"+key,headers=outsider).status_code,404)
            self.assertEqual(self.client.post("/reports",headers=outsider,json=payload).status_code,404)
        self.assertEqual(self.client.get("/reports/"+key,headers=self.worker).status_code,403)
        for fmt,signature in [("xlsx",b"PK"),("pdf",b"%PDF")]:
            exported=self.client.get("/reports/"+key+"/export?format="+fmt,headers=self.admin)
            self.assertEqual(exported.status_code,200,exported.text[:100] if exported.status_code!=200 else "")
            self.assertTrue(exported.content.startswith(signature))
        future={**payload,"day":"2100-01-01"}
        self.assertEqual(self.client.post("/reports",headers=self.admin,json=future).status_code,422)

    def test_energy_estimate_labeled(self):
        r=self.client.post("/energy/assessments",headers=self.admin,json=dict(
            baseline_kwh=100,baseline_units=10,actual_kwh=250,actual_units=20,
            source_evidence="pilot worksheet",comparable_product="same part"))
        self.assertEqual(r.status_code,201,r.text)
        self.assertEqual(r.json()["estimated_savings_kwh"],-50)
        self.assertEqual(r.json()["status"],"estimate-not-verified")
