import json

import click

from tgm.cli.stubs import stub_not_implemented
from tgm.shell.db import DatabaseHandle
from tgm.shell.repos import get_active_criteria


@click.group(name="criteria")
def criteria_group() -> None:
    """Importance criteria: show, recalc, rollback."""


@criteria_group.command(name="show")
@click.option("--scope", type=str, default="global", help="global | chat:<id>.")
@click.pass_obj
def criteria_show(handle: DatabaseHandle, scope: str) -> None:
    """Print active criteria text as JSON."""
    with handle.session_factory() as session:
        criteria = get_active_criteria(session, scope)
    if criteria is None:
        click.echo(json.dumps({"scope": scope, "criteria_text": None, "version": None}, ensure_ascii=False))
        return
    click.echo(
        json.dumps(
            {
                "scope": criteria.scope,
                "version": criteria.version,
                "criteria_text": criteria.criteria_text,
                "updated_at": criteria.updated_at.isoformat()
                if hasattr(criteria.updated_at, "isoformat")
                else str(criteria.updated_at),
            },
            ensure_ascii=False,
        )
    )


@criteria_group.command(name="recalc")
@click.option("--scope", type=str, required=True, help="global | chat:<id>.")
def criteria_recalc(scope: str) -> None:
    """Recalculate criteria from accumulated feedback."""
    stub_not_implemented("EPIC-08 (feedback)")


@criteria_group.command(name="rollback")
@click.option("--scope", type=str, required=True, help="global | chat:<id>.")
@click.option("--version", type=int, required=True, help="Target version to roll back to.")
def criteria_rollback(scope: str, version: int) -> None:
    """Roll back criteria to a specific version."""
    stub_not_implemented("EPIC-04 (repos)")
