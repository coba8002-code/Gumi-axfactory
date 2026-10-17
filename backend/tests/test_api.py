from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_incident_lifecycle():
    assert client.get("/health").json()["status"] == "ok"
    response = client.post("/incidents", json={
        "tenant_id": "demo-factory", "equipment_id": "CNC-07",
        "reason": "tool", "notes": "Tool change required"
    })
    assert response.status_code == 201
    incident_id = response.json()["id"]
    assert client.post(f"/incidents/{incident_id}/actions", json={"action": "Replaced tool"}).status_code == 200
    assert client.get(f"/incidents/{incident_id}").json()["actions"][0]["action"] == "Replaced tool"
