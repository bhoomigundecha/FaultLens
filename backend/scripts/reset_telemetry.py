#!/usr/bin/env python3
"""
FaultLens — show which Postgres the backend really uses, and optionally wipe data.

Connects with the SAME settings the backend uses (backend/.env → DATABASE_URL_SYNC),
so it always hits the right database even if several Postgres servers are running.

    ./venv/bin/python scripts/reset_telemetry.py            # just report
    ./venv/bin/python scripts/reset_telemetry.py --wipe     # empty all FaultLens tables
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.chdir(os.path.join(os.path.dirname(__file__), ".."))   # so .env is found

import psycopg2                                   # noqa: E402
from app.core.config import get_settings          # noqa: E402

TABLES = ["spans", "metric_points", "log_records", "services", "service_dependencies",
          "anomalies", "incidents", "root_cause_analyses", "ai_explanations"]

ap = argparse.ArgumentParser()
ap.add_argument("--wipe", action="store_true", help="TRUNCATE all FaultLens tables")
args = ap.parse_args()

url = get_settings().database_url_sync
safe = url.split("@")[-1]
conn = psycopg2.connect(url)
conn.autocommit = True
cur = conn.cursor()

cur.execute("SELECT version(), current_database(), current_user")
version, dbname, user = cur.fetchone()
print(f"Connected to : {safe}  (db={dbname}, user={user})")
print(f"Server       : {version}")
where = ("Docker container (Linux build)" if "linux" in version.lower()
         else "a Postgres installed directly on this Mac (NOT the faultlens-postgres container)")
print(f"Running in   : {where}")

cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'")
present = {r[0] for r in cur.fetchall()}
print("\nRow counts:")
for t in TABLES:
    if t in present:
        cur.execute(f"SELECT count(*) FROM {t}")
        print(f"  {t:22} {cur.fetchone()[0]:>10,}")
    else:
        print(f"  {t:22} (missing — run: ./venv/bin/alembic upgrade head)")

if args.wipe:
    existing = [t for t in TABLES if t in present]
    if existing:
        cur.execute(f"TRUNCATE {', '.join(existing)} RESTART IDENTITY")
        print(f"\nWiped {len(existing)} tables.")
