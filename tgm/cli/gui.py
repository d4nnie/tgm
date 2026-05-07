import click

from tgm.cli.stubs import stub_not_implemented


@click.command(name="gui")
def gui_command() -> None:
    """Launch the PySide6 GUI."""
    stub_not_implemented("EPIC-10 (GUI)")
