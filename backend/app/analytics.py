"""Pure, reproducible calculations. No claim of verified savings."""
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo


def period_bounds(day, period):
    tz=ZoneInfo("Asia/Seoul")
    if period=="monthly":
        if day.day != 1: raise ValueError("monthly report date must be the first day")
        end=(day.replace(day=28)+timedelta(days=4)).replace(day=1)
    else: end=day+timedelta(days=1)
    return (datetime.combine(day,time(),tz).astimezone(timezone.utc),
            datetime.combine(end,time(),tz).astimezone(timezone.utc))


def downtime_minutes(rows,start,end):
    groups={}
    for row in rows:
        a=max(start,row["started_at"]);b=min(end,row["ended_at"] or end)
        if a < b: groups.setdefault(str(row["equipment_id"]),[]).append((a,b))
    seconds=0
    for spans in groups.values():
        spans.sort();a,b=spans[0]
        for x,y in spans[1:]:
            if x<=b: b=max(b,y)
            else: seconds+=(b-a).total_seconds();a,b=x,y
        seconds+=(b-a).total_seconds()
    return seconds/60


def energy_summary(rows,start,end):
    measured=estimated=coverage=0.0
    bad=0
    for row in rows:
        if row["quality"]=="bad": bad+=1;continue
        finish=row["observed_at"];seconds=row["interval_seconds"]
        begin=finish-timedelta(seconds=seconds)
        overlap=max(0,(min(end,finish)-max(start,begin)).total_seconds())
        fraction=overlap/seconds
        if fraction==1 and row["quality"]=="good" and row["source"]!="simulator":
            measured+=row["value"];coverage+=overlap
        else: estimated+=row["value"]*fraction
    return dict(measured_kwh=measured,estimated_kwh=estimated,bad_readings=bad,
                measured_coverage_ratio=min(1,coverage/(end-start).total_seconds()),
                limitations=["Single selected meter only; do not sum main and sub-meters.",
                             "Partial boundary intervals are prorated estimates; gaps are not filled.",
                             "Simulator/estimated samples are excluded from measured totals."])


def production_adjusted(baseline_kwh,baseline_units,actual_kwh,actual_units):
    if baseline_units<=0 or actual_units<=0: raise ValueError("positive comparable production required")
    expected=baseline_kwh/baseline_units*actual_units
    return dict(adjusted_baseline_kwh=expected,estimated_savings_kwh=expected-actual_kwh,
                status="estimate-not-verified",
                limitations=["Production-only normalization; product mix, weather and operating hours are not adjusted.",
                             "Negative savings retained. No cash benefit or certified carbon reduction claimed."])
