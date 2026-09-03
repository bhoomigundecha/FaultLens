#!/usr/bin/env python3
"""
FaultLens Live Incident Monitor — continuous console for SREs & Developers.

Continuously polls FaultLens for newly diagnosed incidents in production.
When an incident is detected, displays:
  1. 🚨 What is going down
  2. 🔍 Root cause and causal chain
  3. 📊 Telemetry evidence (metrics, logs, traces)
  4. 🛠️ What you can fix (actionable remediation steps)

Usage:
  python tests/monitor.py [--url http://localhost:8000]
"""

import asyncio
import click
import httpx
import sys
import time

seen_incident_ids = set()


@click.command()
@click.option("--url", default="http://localhost:8000", help="FaultLens API URL")
@click.option("--poll-interval", default=5, help="Polling interval in seconds")
def main(url, poll_interval):
    """Continuously monitor FaultLens for live production incidents and remediation advice."""
    click.echo("\n" + "═" * 78)
    click.echo("  🛡️  FaultLens Live Incident Intelligence Monitor")
    click.echo(f"  Watching: {url}/v1/incidents (polling every {poll_interval}s)")
    click.echo("  Status  : WAITING FOR PRODUCTION TELEMETRY ANOMALIES...")
    click.echo("═" * 78 + "\n")

    async def _loop():
        async with httpx.AsyncClient() as client:
            while True:
                try:
                    resp = await client.get(f"{url}/v1/incidents", timeout=8)
                    if resp.status_code == 200:
                        incidents = resp.json()
                        for inc in incidents:
                            inc_id = inc.get("incident_id")
                            if inc_id and inc_id not in seen_incident_ids:
                                seen_incident_ids.add(inc_id)
                                _display_incident(inc)
                except httpx.ConnectError:
                    pass
                except Exception as e:
                    click.echo(f"  [Monitor Warning] {e}")

                await asyncio.sleep(poll_interval)

    asyncio.run(_loop())


def _display_incident(inc: dict):
    # Terminal alert bell
    sys.stdout.write("\a")
    sys.stdout.flush()

    inc_id = inc.get("incident_id", "N/A")
    service = inc.get("service_id", "unknown")
    failure_type = inc.get("failure_type", "UNHANDLED_EXCEPTION")
    team = inc.get("team_routing", "Backend")
    confidence = inc.get("confidence") or 0.0
    report = inc.get("rca_report", "")

    click.echo("\n" + "█" * 78)
    click.echo(f"  🚨 PRODUCTION INCIDENT DETECTED — {time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    click.echo(f"  Incident ID  : {inc_id}")
    click.echo(f"  Service      : {service}")
    click.echo(f"  Failure Type : {failure_type} ({confidence:.0%} confidence)")
    click.echo(f"  Assigned Team: {team}")
    click.echo("█" * 78)

    if report:
        click.echo("\n" + report.strip())
    else:
        click.echo("\n  [Investigating telemetry signals... Full report streaming soon]")

    click.echo("\n" + "─" * 78 + "\n")


if __name__ == "__main__":
    main()
