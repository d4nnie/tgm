import click

from tgm.cli.stubs import stub_not_implemented


@click.group(name="highlight")
def highlight_group() -> None:
    """Highlights: list and mark-important."""


@highlight_group.command(name="list")
@click.argument("scope", type=str)
@click.option("--unseen", is_flag=True, default=False, help="Only unseen highlights.")
def highlight_list(scope: str, unseen: bool) -> None:
    """Print highlights as JSON."""
    stub_not_implemented("EPIC-04 (repos)")


@highlight_group.command(name="mark-important")
@click.argument("message_ids", type=int, nargs=-1, required=True)
@click.option("--scope", type=str, required=True, help="chat:<id> | global.")
@click.option("--comment", type=str, default="", help="Free-form feedback comment.")
def highlight_mark_important(message_ids: tuple[int, ...], scope: str, comment: str) -> None:
    """Record a feedback marker for the given message ids."""
    stub_not_implemented("EPIC-04 (repos) + EPIC-08 (feedback)")
