import hashlib
import os
import unittest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app
from app.db import connect


@unittest.skipUnless(os.getenv("DATABASE_URL"), "requires migrated PostgreSQL")
class Fixture(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.tenant, self.factory = uuid4(), uuid4()
        self.admin = self.identity("admin")
        self.worker = self.identity("worker")
        self.supervisor = self.identity("supervisor")
        self.other = self.identity("admin", uuid4(), uuid4())
        self.other_factory = self.identity("admin", self.tenant, uuid4())
        self.device = self.identity("device")
        self.eq = self.client.post("/equipment", headers=self.admin, json={"name":"CNC-01"}).json()["id"]
        self.payload = dict(id=str(uuid4()), equipment_id=self.eq, reason="tool", notes="공구 마모",
                            started_at=(datetime.now(timezone.utc)-timedelta(hours=1)).isoformat())

    def identity(self, role, tenant=None, factory=None):
        token = str(uuid4()) + str(uuid4())
        with connect() as db:
            db.execute("INSERT INTO identities(id,tenant_id,factory_id,role,token_hash) VALUES (%s,%s,%s,%s,%s)",
                       (uuid4(), tenant or self.tenant, factory or self.factory, role, hashlib.sha256(token.encode()).hexdigest()))
        return {"Authorization":"Bearer "+token}

    def create(self):
        response = self.client.post("/incidents", headers=self.worker, json=self.payload)
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()["id"]


class APITest(Fixture):
    def test_revoked_credentials_and_append_only_audit(self):
        from psycopg import errors
        identity=self.client.get("/me",headers=self.worker).json()["id"]
        with connect() as db:
            db.execute("UPDATE identities SET active=false WHERE id=%s",(identity,))
        self.assertEqual(self.client.get("/equipment",headers=self.worker).status_code,401)
        with self.assertRaises(errors.RaiseException):
            with connect() as db:
                db.execute("DELETE FROM audit_events WHERE tenant_id=%s AND factory_id=%s",(self.tenant,self.factory))

    def test_auth_scope(self):
        self.assertEqual(self.client.get("/equipment").status_code, 401)
        self.assertEqual(self.client.get("/equipment", headers=self.device).status_code, 403)
        self.assertEqual(self.client.post("/equipment", headers=self.worker, json={"name":"x"}).status_code, 403)
        item = self.create()
        for outsider in [self.other, self.other_factory]:
            self.assertEqual(self.client.get("/equipment", headers=outsider).json(), [])
            self.assertEqual(self.client.get("/incidents/"+item, headers=outsider).status_code, 404)
            self.assertEqual(self.client.post("/incidents", headers=outsider, json=self.payload).status_code, 404)

    def test_lifecycle_retry_persistence(self):
        item = self.create()
        self.assertEqual(self.create(), item)
        self.assertEqual(self.client.post("/incidents", headers=self.worker, json={**self.payload,"notes":"변경"}).status_code, 409)
        action = {"id":str(uuid4()),"action":"공구 교체","outcome":"정상 복구"}
        for _ in range(2):
            self.assertEqual(self.client.post(f"/incidents/{item}/actions", headers=self.worker, json=action).status_code, 200)
        approval = {"resolved":True,"evidence":"재가동 확인","ended_at":datetime.now(timezone.utc).isoformat()}
        self.assertEqual(self.client.post(f"/incidents/{item}/approve", headers=self.worker, json=approval).status_code, 403)
        self.assertEqual(self.client.post(f"/incidents/{item}/approve", headers=self.supervisor, json=approval).status_code, 200)
        saved = TestClient(app).get(f"/incidents/{item}", headers=self.worker).json()
        self.assertTrue(saved["approved"])
        self.assertEqual(len(saved["actions"]), 1)
        self.assertEqual(self.create(), item)
        self.assertEqual(len(self.client.get("/audit", headers=self.admin).json()), 4)
        self.assertEqual(self.client.get("/audit", headers=self.other).json(), [])

    def test_validation_self_review(self):
        self.assertEqual(self.client.post("/incidents", headers=self.worker, json={**self.payload,"tenant_id":"forged"}).status_code, 422)
        item = self.client.post("/incidents", headers=self.supervisor, json=self.payload).json()["id"]
        self.client.post(f"/incidents/{item}/actions", headers=self.worker, json={"action":"조치","outcome":"해결"})
        self.assertEqual(self.client.post(f"/incidents/{item}/approve", headers=self.supervisor,
            json={"resolved":True,"evidence":"확인","ended_at":datetime.now(timezone.utc).isoformat()}).status_code, 403)
