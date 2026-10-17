from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="Gumi AX Factory MVP API", version="0.1.0")

# Development-only ephemeral state. Replace with authenticated tenant-scoped DB.
incidents: dict[str, dict] = {}


class IncidentIn(BaseModel):
    tenant_id: str = Field(min_length=1, max_length=64)
    equipment_id: str = Field(min_length=1, max_length=64)
    reason: Literal["fault", "tool", "material", "setup", "other"]
    notes: str = Field(default="", max_length=4000)


class ActionIn(BaseModel):
    action: str = Field(min_length=1, max_length=4000)


@app.get("/health")
def health():
    return {"status": "ok", "mode": "development-only"}


@app.post("/incidents", status_code=201)
def create_incident(body: IncidentIn):
    item = {
        "id": str(uuid4()),
        **body.model_dump(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "actions": [],
        "approved": False,
    }
    incidents[item["id"]] = item
    return item


@app.get("/incidents/{incident_id}")
def get_incident(incident_id: str):
    item = incidents.get(incident_id)
    if item is None:
        raise HTTPException(404, "Incident not found")
    return item


@app.post("/incidents/{incident_id}/actions")
def add_action(incident_id: str, body: ActionIn):
    item = incidents.get(incident_id)
    if item is None:
        raise HTTPException(404, "Incident not found")
    item["actions"].append({"action": body.action, "at": datetime.now(timezone.utc).isoformat()})
    return item
