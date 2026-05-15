import click

from tgm.cli.stubs import stub_not_implemented
from tgm.shell.platform import require_single_instance


@click.group(name="digest")
def digest_group() -> None:
    """Digest tick and read."""


@digest_group.command(name="run")
@click.option("--scope", type=str, required=True, help="<chat-id> | global | all.")
@require_single_instance
def digest_run(scope: str) -> None:
    """Run one tick of the worker right now."""
    stub_not_implemented("EPIC-07 (worker)")


@digest_group.command(name="get")
@click.argument("scope", type=str)
@click.option("--last", type=int, default=1, help="Number of recent digests to fetch.")
@require_single_instance
def digest_get(scope: str, last: int) -> None:
    """Print last N digests as JSON."""
    stub_not_implemented("EPIC-04 (repos)")
