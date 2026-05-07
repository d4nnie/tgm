import click

from tgm.cli.stubs import stub_not_implemented


@click.group(name="criteria")
def criteria_group() -> None:
    """Importance criteria: show, recalc, rollback."""


@criteria_group.command(name="show")
@click.option("--scope", type=str, default="global", help="global | chat:<id>.")
@click.option("--version", type=int, default=None, help="Specific version (default: current).")
def criteria_show(scope: str, version: int | None) -> None:
    """Print criteria text as JSON."""
    stub_not_implemented("EPIC-04 (repos)")


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
