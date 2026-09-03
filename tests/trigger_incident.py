#!/usr/bin/env python3
"""
Trigger a synthetic incident for testing — sends sample OTLP payloads
to the FaultLens ingestion API and waits for a report to be generated.

Usage: python tests/trigger_incident.py [--service demo-store] [--faultlens-url http://localhost:8000]
"""

import asyncio
import json
import pathlib
import click
import httpx

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


async def send_fixture(client: httpx.AsyncClient, url: str, signal_type: str) -> bool:
    fixture_file = FIXTURES / f"sample_otlp_{signal_type}.json"
    if not fixture_file.exists():
        click.echo(f"  ⚠️  No fixture found: {fixture_file}")
        return False
    payload = json.loads(fixture_file.read_text())
    resp = await client.post(f"{url}/v1/ingest/{signal_type}", json=payload, timeout=10)
    click.echo(f"  POST /v1/ingest/{signal_type} → {resp.status_code} {resp.text[:80]}")
    return resp.status_code == 202


@click.command()
@click.option("--service",       default="demo-store",          help="Service ID to attribute signals to")
@click.option("--faultlens-url", default="http://localhost:8000", help="FaultLens ingestion URL")
@click.option("--repeat",        default=5,  show_default=True,  help="How many times to send each fixture (simulates volume)")
@click.option("--interval-s",    default=3,  show_default=True,  help="Seconds between repeats")
def main(service, faultlens_url, repeat, interval_s):
    """Send synthetic OTLP signals to FaultLens to trigger an AI_RATE_LIMIT_EXCEEDED incident."""
    async def _run():
        click.echo(f"\nTriggering synthetic incident for service='{service}' …")
        click.echo(f"FaultLens URL: {faultlens_url}\n")

        async with httpx.AsyncClient() as client:
            for i in range(repeat):
                click.echo(f"Round {i+1}/{repeat}:")
                for signal in ["metrics", "logs", "traces"]:
                    await send_fixture(client, faultlens_url, signal)
                if i < repeat - 1:
                    await asyncio.sleep(interval_s)

        click.echo(f"\n✅ Done. Signals sent {repeat}x.")
        click.echo(f"   Wait ~60s then run: python tests/verify_incident.py")

    asyncio.run(_run())


if __name__ == "__main__":
    main()
