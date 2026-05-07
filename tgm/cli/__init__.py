import click

from tgm.cli import auth, chat, digest, highlight
from tgm.shell.db import connect, migrate, resolve_db_path
from tgm.shell.platform import ensure_user_data_dir


@click.group(invoke_without_command=True, context_settings={"help_option_names": ["-h", "--help"]})
@click.pass_context
def cli_main(context: click.Context) -> None:
    """Telegram Monitor — personal desktop digest of Telegram chats."""
    ensure_user_data_dir()
    _migrate_database()

    if context.invoked_subcommand is None:
        raise click.ClickException("GUI not yet implemented (depends on EPIC-10)")


def _migrate_database() -> None:
    connection = connect(resolve_db_path())
    try:
        migrate(connection)
    finally:
        connection.close()


cli_main.add_command(auth.auth_group)
cli_main.add_command(chat.chat_group)
cli_main.add_command(digest.digest_group)
cli_main.add_command(highlight.highlight_group)
