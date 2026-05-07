import click

from tgm.cli.stubs import stub_not_implemented


@click.group(name="auth")
def auth_group() -> None:
    """Telegram session: login and status."""


@auth_group.command(name="login")
def auth_login() -> None:
    """Interactive login: api_id / api_hash / phone / SMS code / 2FA."""
    stub_not_implemented("EPIC-03 (Telethon)")


@auth_group.command(name="status")
def auth_status() -> None:
    """Print JSON: connection, provider, worker state."""
    stub_not_implemented("EPIC-03 (Telethon) + EPIC-05 (LLM provider) + EPIC-07 (worker)")
