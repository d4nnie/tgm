import click

from tgm.cli.stubs import stub_not_implemented


@click.group(name="chat")
def chat_group() -> None:
    """Chat whitelist: list, add, remove, profile."""


@chat_group.command(name="list")
def chat_list() -> None:
    """Print all dialogs in the account as JSON."""
    stub_not_implemented("EPIC-03 (Telethon)")


@chat_group.command(name="add")
@click.argument("chat_id", type=int)
@click.option("--period", type=int, default=None, help="Per-chat tick period in minutes.")
def chat_add(chat_id: int, period: int | None) -> None:
    """Add a chat to the whitelist (no backfill)."""
    stub_not_implemented("EPIC-03 (Telethon) + EPIC-04 (repos)")


@chat_group.command(name="remove")
@click.argument("chat_id", type=int)
def chat_remove(chat_id: int) -> None:
    """Remove a chat from the whitelist (history retained)."""
    stub_not_implemented("EPIC-04 (repos)")


@chat_group.command(name="profile")
@click.argument("chat_id", type=int)
@click.option("--description", type=str, default=None, help="Chat description prompt.")
@click.option("--period", type=int, default=None, help="Per-chat tick period in minutes.")
def chat_profile(chat_id: int, description: str | None, period: int | None) -> None:
    """Show or edit chat profile."""
    stub_not_implemented("EPIC-04 (repos)")
