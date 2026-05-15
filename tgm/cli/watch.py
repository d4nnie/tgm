import click

from tgm.cli.stubs import stub_not_implemented
from tgm.shell.platform import require_single_instance


@click.command(name="watch")
@require_single_instance
def watch_command() -> None:
    """Headless worker; stream NDJSON events to stdout until Ctrl+C."""
    stub_not_implemented("EPIC-07 (worker)")
