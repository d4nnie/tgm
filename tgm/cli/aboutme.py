import click

from tgm.cli.stubs import stub_not_implemented


@click.group(name="about-me")
def about_me_group() -> None:
    """User self-description used in prompts."""


@about_me_group.command(name="show")
def about_me_show() -> None:
    """Print current about-me text."""
    stub_not_implemented("EPIC-04 (repos)")


@about_me_group.command(name="set")
@click.argument("text", type=str)
def about_me_set(text: str) -> None:
    """Replace about-me text."""
    stub_not_implemented("EPIC-04 (repos)")
