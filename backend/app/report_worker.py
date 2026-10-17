"""Run once hourly via scheduler; API unique period key prevents duplicates."""
import json
import os
import time
import urllib.request
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo


def run():
    today=datetime.now(ZoneInfo("Asia/Seoul")).date()
    periods=[("daily",today-timedelta(days=1))]
    # Always retry previous month's snapshot; safe after a missed first-day run.
    periods.append(("monthly",(today.replace(day=1)-timedelta(days=1)).replace(day=1)))
    for period,day in periods:
        payload={"period":period,"day":str(day),"sensor_id":os.getenv("REPORT_SENSOR_ID") or None}
        request=urllib.request.Request(os.environ["REPORT_API_URL"]+"/reports",
            data=json.dumps(payload).encode(),method="POST",
            headers={"Authorization":"Bearer "+os.environ["REPORT_TOKEN"],"Content-Type":"application/json"})
        with urllib.request.urlopen(request,timeout=30) as response:
            if response.status!=201:raise RuntimeError("report generation failed")


if __name__=="__main__":
    while True:
        try:run()
        except Exception as e:print("Report run failed:",type(e).__name__,flush=True)
        time.sleep(3600)
