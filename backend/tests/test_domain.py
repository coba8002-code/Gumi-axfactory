import unittest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from pydantic import ValidationError
from app.main import IncidentIn
from app.telemetry import ReadingIn


class DomainTest(unittest.TestCase):
    def test_naive_incident_timestamp(self):
        with self.assertRaises(ValidationError):
            IncidentIn(equipment_id=uuid4(),reason="tool",started_at="2026-01-01T00:00:00")

    def test_reading_contract(self):
        data=dict(sensor_id=uuid4(),event_id=uuid4(),observed_at=datetime.now(timezone.utc),
                  metric="energy_kwh_interval",value=1,unit="kWh",interval_seconds=60,
                  quality="good",source="modbus_tcp",firmware_version="test")
        self.assertEqual(ReadingIn(**data).value,1)
        for changes in [{"value":float("nan")},{"value":-1},{"unit":"kW"},{"interval_seconds":None},
                        {"observed_at":datetime.now(timezone.utc)+timedelta(days=1)}]:
            with self.assertRaises(ValidationError):ReadingIn(**{**data,**changes})
