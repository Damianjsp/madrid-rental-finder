"""CLI entrypoints for Madrid Rental Finder scrapers and maintenance tasks."""

from __future__ import annotations

import importlib
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import click

PORTAL_MODULES: dict[str, str] = {
    "pisos": "pisos",
    "enalquiler": "enalquiler",
    "habitaclia": "habitaclia",
    "yaencontre": "yaencontre",
    "tranquiler": "tranquiler",
}
PORTAL_CHOICES: tuple[str, ...] = tuple([*PORTAL_MODULES.keys(), "all"])


@dataclass(slots=True)
class ScraperSummary:
    portal: str
    stats: dict[str, int]


def _import_scraper_module(portal_key: str):
    module_name = PORTAL_MODULES[portal_key]
    return importlib.import_module(f"mrf.scrapers.{module_name}")


def _get_scraper_class(module: Any, portal_key: str):
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if isinstance(attr, type) and getattr(attr, "portal_key", None) == portal_key:
            return attr
    raise click.ClickException(f"No scraper class found for portal '{portal_key}'.")


def _run_single_scraper(portal_key: str) -> ScraperSummary:
    module = _import_scraper_module(portal_key)
    scraper_class = _get_scraper_class(module, portal_key)
    scraper = scraper_class()
    stats = scraper.run()
    return ScraperSummary(portal=portal_key, stats=stats)


def _backend_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _run_seed_script() -> None:
    script_path = _backend_root() / "scripts" / "seed.py"
    if not script_path.exists():
        raise click.ClickException(f"Seed script not found: {script_path}")
    completed = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=str(_backend_root()),
        check=False,
    )
    if completed.returncode != 0:
        raise click.ClickException(f"Seed script failed with exit code {completed.returncode}.")


def collect_status() -> list[dict[str, Any]]:
    from sqlalchemy import func

    from mrf.db.models import Listing, Portal, ScraperRun
    from mrf.db.session import get_db

    with get_db() as db:
        portals = db.query(Portal).order_by(Portal.key.asc()).all()
        rows: list[dict[str, Any]] = []
        for portal in portals:
            latest_run = (
                db.query(ScraperRun)
                .filter(ScraperRun.portal_id == portal.id)
                .order_by(ScraperRun.started_at.desc(), ScraperRun.id.desc())
                .first()
            )
            active_count = (
                db.query(func.count(Listing.id))
                .filter(Listing.portal_id == portal.id, Listing.is_active.is_(True))
                .scalar()
            )
            total_count = (
                db.query(func.count(Listing.id))
                .filter(Listing.portal_id == portal.id)
                .scalar()
            )
            rows.append(
                {
                    "portal": portal.key,
                    "active_listings": int(active_count or 0),
                    "total_listings": int(total_count or 0),
                    "latest_run_status": latest_run.status if latest_run else None,
                    "latest_run_started_at": latest_run.started_at.isoformat() if latest_run else None,
                    "latest_run_finished_at": latest_run.finished_at.isoformat() if latest_run and latest_run.finished_at else None,
                    "latest_run_seen": latest_run.listings_seen if latest_run else 0,
                    "latest_run_new": latest_run.listings_new if latest_run else 0,
                    "latest_run_updated": latest_run.listings_updated if latest_run else 0,
                    "latest_run_error": latest_run.error_message if latest_run else None,
                }
            )
        return rows


@click.group()
def main() -> None:
    """Madrid Rental Finder CLI."""


@main.command()
@click.argument("portal", type=click.Choice(PORTAL_CHOICES, case_sensitive=False))
def scrape(portal: str) -> None:
    """Run one scraper or all scrapers sequentially."""
    normalized_portal = portal.lower()
    portals = list(PORTAL_MODULES) if normalized_portal == "all" else [normalized_portal]

    summaries: list[ScraperSummary] = []
    for portal_key in portals:
        click.echo(f"Running scraper: {portal_key}")
        summary = _run_single_scraper(portal_key)
        summaries.append(summary)
        click.echo(json.dumps(asdict(summary), indent=2, sort_keys=True, default=str))

    if len(summaries) > 1:
        aggregate = {
            "seen": sum(item.stats.get("seen", 0) for item in summaries),
            "new": sum(item.stats.get("new", 0) for item in summaries),
            "updated": sum(item.stats.get("updated", 0) for item in summaries),
        }
        click.echo(json.dumps({"aggregate": aggregate}, indent=2, sort_keys=True))


@main.command()
@click.option("--stale-after-days", default=7, show_default=True, type=int)
def reconcile(stale_after_days: int) -> None:
    """Mark listings inactive when they have not been seen recently."""
    from mrf.reconcile import reconcile_listings

    summary = reconcile_listings(stale_after_days=stale_after_days)
    click.echo(json.dumps(summary, indent=2, sort_keys=True))


@main.command()
def seed() -> None:
    """Run the backend seed script."""
    _run_seed_script()
    click.echo("Seed complete")


@main.command()
def status() -> None:
    """Show per-portal listing and scraper run status."""
    click.echo(json.dumps(collect_status(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
