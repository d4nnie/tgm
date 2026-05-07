import click

from tgm.cli.stubs import stub_not_implemented


@click.command(name="watch")
def watch_command() -> None:
    """Headless worker; stream NDJSON events to stdout until Ctrl+C."""
    stub_not_implemented("EPIC-07 (worker)")
