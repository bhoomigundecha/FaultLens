#!/usr/bin/env python3
"""
Verify that FaultLens generated an incident and RCA report.

Usage: python tests/verify_incident.py [--faultlens-url http://localhost:8000]
"""

import asyncio
import click
import httpx


@click.command()
@click.option("--faultlens-url", default="http://localhost:8000")
@click.option("--wait",          default=0,   help="Seconds to wait before checking")
@click.option("--service",       default=None, help="Filter by service ID")
def main(faultlens_url, wait, service):
    """Fetch and display recent incidents from FaultLens."""
    async def _run():
        if wait:
            click.echo(f"Waiting {wait}s for agent to process …")
            await asyncio.sleep(wait)

        async with httpx.AsyncClient() as client:
            url = f"{faultlens_url}/v1/incidents"
            if service:
                url += f"?service_id={service}"

            resp = await client.get(url, timeout=10)
            if resp.status_code != 200:
                click.echo(f"❌ Could not fetch incidents: {resp.status_code} {resp.text}", err=True)
                return

            incidents = resp.json()
            if not incidents:
                click.echo("⚠️  No incidents found yet. Try again in a moment.")
                return

            click.echo(f"\n{'='*70}")
            click.echo(f" FaultLens Incidents ({len(incidents)} found)")
            click.echo(f"{'='*70}\n")

            for inc in incidents[:5]:
                click.echo(f"Incident: {inc.get('incident_id', 'N/A')}")
                click.echo(f"  Service:      {inc.get('service_id', 'N/A')}")
                click.echo(f"  Failure Type: {inc.get('failure_type', 'pending')}")
                click.echo(f"  Confidence:   {(inc.get('confidence') or 0):.0%}")
                click.echo(f"  Team:         {inc.get('team_routing', 'N/A')}")
                click.echo(f"  Status:       {inc.get('status', 'N/A')}")
                click.echo(f"  Created:      {inc.get('created_at', 'N/A')}")

                report = inc.get("rca_report", "")
                if report:
                    click.echo(f"\n  ═══════════════════ ROOT CAUSE ANALYSIS & REMEDIATION ═══════════════════")
                    click.echo(f"{report}")
                    click.echo(f"  ═════════════════════════════════════════════════════════════════════════\n")
                click.echo()

    asyncio.run(_run())


if __name__ == "__main__":
    main()
