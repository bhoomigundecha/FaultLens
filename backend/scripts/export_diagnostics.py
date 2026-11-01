#!/usr/bin/env python3
"""
FaultLens — export diagnostics for tuning / the fault scorecard (read-only).

Writes two files into FaultLens/diagnostics/ :
  red_stats_<time>.csv   one row per (service, minute) for the retained window:
                         requests, errors, error_rate, p50/p95/max latency (SERVER/CONSUMER spans)
  incidents_<time>.json  every anomaly + incident + RCA + AI explanation in the DB

    ./venv/bin/python scripts/export_diagnostics.py
"""
import csv
import datetime as dt
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
os.chdir(os.path.join(HERE, ".."))   # so .env is found

import psycopg2                       # noqa: E402
import psycopg2.extras                # noqa: E402
from app.core.config import get_settings  # noqa: E402

out_dir = os.path.join(HERE, "..", "..", "diagnostics")
os.makedirs(out_dir, exist_ok=True)
stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")

conn = psycopg2.connect(get_settings().database_url_sync)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# ── per-service, per-minute RED stats ─────────────────────────────────────────
cur.execute("""
    SELECT service_name,
           to_char(to_timestamp(start_time_unix_nano / 1e9) AT TIME ZONE 'Asia/Kolkata',
                   'HH24:MI')                                         AS minute,
           count(*)                                                   AS requests,
           count(*) FILTER (WHERE status_code = 2)                    AS errors,
           round((percentile_cont(0.50) WITHIN GROUP
                 (ORDER BY end_time_unix_nano - start_time_unix_nano) / 1e6)::numeric, 1) AS p50_ms,
           round((percentile_cont(0.95) WITHIN GROUP
                 (ORDER BY end_time_unix_nano - start_time_unix_nano) / 1e6)::numeric, 1) AS p95_ms,
           round((max(end_time_unix_nano - start_time_unix_nano) / 1e6)::numeric, 1)      AS max_ms
    FROM spans
    WHERE kind IN (2, 5) AND service_name IS NOT NULL
    GROUP BY service_name, minute
    ORDER BY service_name, minute
""")
rows = cur.fetchall()
red_path = os.path.join(out_dir, f"red_stats_{stamp}.csv")
with open(red_path, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=["service_name", "minute", "requests", "errors",
                                       "error_rate", "p50_ms", "p95_ms", "max_ms"])
    w.writeheader()
    for r in rows:
        r["error_rate"] = round(r["errors"] / r["requests"], 3) if r["requests"] else 0
        w.writerow(r)

# ── anomalies, incidents, RCA, AI ─────────────────────────────────────────────
def ist(ns):
    if not ns:
        return None
    return dt.datetime.fromtimestamp(ns / 1e9).strftime("%H:%M:%S")

def dump(sql):
    cur.execute(sql)
    return [dict(r) for r in cur.fetchall()]

anomalies = dump("SELECT * FROM anomalies ORDER BY id")
incidents = dump("SELECT * FROM incidents ORDER BY id")
rcas      = {r["incident_id"]: r for r in dump("SELECT * FROM root_cause_analyses")}
ais       = {r["incident_id"]: r for r in dump("SELECT * FROM ai_explanations")}

for a in anomalies:
    for k in ("detected_at_unix_nano", "resolved_at_unix_nano", "last_firing_unix_nano"):
        a[k.replace("_unix_nano", "")] = ist(a.pop(k, None))
for i in incidents:
    i["created_at"]  = ist(i.pop("created_at_unix_nano", None))
    i["resolved_at"] = ist(i.pop("resolved_at_unix_nano", None))
    rca = rcas.get(i["id"])
    i["rca"] = rca and {k: rca[k] for k in ("root_cause_service", "confidence", "propagation_path")}
    ai = ais.get(i["id"])
    i["ai"] = ai and {k: ai[k] for k in ("root_cause_service", "fault_type", "confidence_label",
                                         "human_summary", "remediation_steps", "model")}

inc_path = os.path.join(out_dir, f"incidents_{stamp}.json")
with open(inc_path, "w") as fh:
    json.dump({"anomalies": anomalies, "incidents": incidents}, fh, indent=2, default=str)

print(f"wrote {len(rows)} service-minutes → {os.path.relpath(red_path)}")
print(f"wrote {len(incidents)} incidents, {len(anomalies)} anomalies → {os.path.relpath(inc_path)}")
