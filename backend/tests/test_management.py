from datetime import datetime, timezone, timedelta
from uuid import uuid4
import test_api as support


class ManagementTest(support.Fixture):
    def sensor(self):
        device_id=self.client.get("/me",headers=self.device).json()["id"]
        sid=str(uuid4())
        r=self.client.post("/sensors",headers=self.admin,json={"id":sid,"equipment_id":self.eq,
            "device_id":device_id,"name":"Power meter"})
        self.assertEqual(r.status_code,201)
        return sid

    def test_monitoring_roles_and_isolation(self):
        self.create();self.sensor()
        summary=self.client.get("/monitoring",headers=self.supervisor).json()["summary"]
        self.assertEqual(summary["equipment"],1);self.assertEqual(summary["pending_incidents"],1)
        self.assertEqual(summary["attention_streams"],1)
        for outsider in [self.other,self.other_factory]:
            self.assertEqual(self.client.get("/monitoring",headers=outsider).json()["summary"]["equipment"],0)
        for disallowed in [self.worker,self.device]:
            self.assertEqual(self.client.get("/monitoring",headers=disallowed).status_code,403)

    def test_stale_series_and_sensor_isolation(self):
        sid=self.sensor()
        old=datetime.now(timezone.utc)-timedelta(minutes=10)
        self.client.post("/readings",headers=self.device,json={"sensor_id":sid,"event_id":str(uuid4()),
            "observed_at":old.isoformat(),"metric":"power_kw","value":12,"unit":"kW",
            "quality":"estimated","source":"simulator","firmware_version":"test"})
        sensor=self.client.get("/monitoring",headers=self.admin).json()["sensors"][0]
        self.assertEqual(sensor["stream_status"],"attention")
        self.assertEqual(sensor["source"],"simulator")
        self.assertEqual(len(self.client.get("/monitoring/readings",headers=self.admin,params={"sensor_id":sid}).json()["points"]),1)
        self.assertEqual(self.client.get("/monitoring/readings",headers=self.other,params={"sensor_id":sid}).status_code,404)

    def test_account_scope_no_credentials_and_revocation(self):
        rows=self.client.get("/management/identities",headers=self.admin).json()
        self.assertTrue(all(set(x)=={"id","role","active"} for x in rows))
        self.assertEqual(self.client.get("/management/identities",headers=self.supervisor).status_code,403)
        worker_id=self.client.get("/me",headers=self.worker).json()["id"]
        path="/management/identities/"+worker_id+"/deactivate"
        self.assertEqual(self.client.post(path,headers=self.other).status_code,404)
        self.assertEqual(self.client.post(path,headers=self.admin).status_code,200)
        self.assertEqual(self.client.get("/me",headers=self.worker).status_code,401)
        self_id=self.client.get("/me",headers=self.admin).json()["id"]
        self.assertEqual(self.client.post("/management/identities/"+self_id+"/deactivate",headers=self.admin).status_code,409)
