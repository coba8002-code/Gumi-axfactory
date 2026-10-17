import unittest
from datetime import date,timedelta
from app.analytics import period_bounds,downtime_minutes,energy_summary,production_adjusted


class AnalyticsTest(unittest.TestCase):
    def test_month_and_korean_timezone(self):
        a,b=period_bounds(date(2024,2,1),"monthly")
        self.assertEqual((b-a).days,29);self.assertEqual(a.hour,15)
        with self.assertRaises(ValueError):period_bounds(date(2024,2,2),"monthly")

    def test_overlap_and_period_clipping(self):
        a,b=period_bounds(date(2026,1,1),"daily")
        rows=[dict(equipment_id="a",started_at=a-timedelta(hours=1),ended_at=a+timedelta(hours=1)),
              dict(equipment_id="a",started_at=a,ended_at=a+timedelta(hours=2)),
              dict(equipment_id="b",started_at=b-timedelta(minutes=30),ended_at=None)]
        self.assertEqual(downtime_minutes(rows,a,b),150)

    def test_measured_estimated_bad_and_partial(self):
        a,b=period_bounds(date(2026,1,1),"daily")
        base=dict(observed_at=a+timedelta(hours=1),interval_seconds=3600,value=10,quality="good",source="modbus_tcp")
        rows=[base,{**base,"source":"simulator"},{**base,"quality":"bad"},
              {**base,"observed_at":a+timedelta(minutes=30)}]
        result=energy_summary(rows,a,b)
        self.assertEqual(result["measured_kwh"],10)
        self.assertEqual(result["estimated_kwh"],15)
        self.assertEqual(result["bad_readings"],1)
        self.assertAlmostEqual(result["measured_coverage_ratio"],1/24)

    def test_negative_savings_not_hidden(self):
        r=production_adjusted(100,10,250,20)
        self.assertEqual(r["estimated_savings_kwh"],-50)
        self.assertEqual(r["status"],"estimate-not-verified")
        with self.assertRaises(ValueError):production_adjusted(1,0,1,1)
