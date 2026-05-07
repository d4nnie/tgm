import click

from tgm.cli import aboutme, auth, chat, criteria, digest, gui, highlight, llm, watch
from tgm.shell.db import connect, migrate, resolve_db_path
from tgm.shell.platform import ensure_user_data_dir


@click.group(invoke_without_command=True, context_settings={"help_option_names": ["-h", "--help"]})
@click.pass_context
def cli_main(context: click.Context) -> None:
    """Telegram Monitor — personal desktop digest of Telegram chats."""
    ensure_user_data_dir()
    _migrate_database()

    if context.invoked_subcommand is None:
        context.invoke(gui.gui_command)


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
cli_main.add_command(criteria.criteria_group)
cli_main.add_command(aboutme.about_me_group)
cli_main.add_command(llm.llm_group)
cli_main.add_command(watch.watch_command)
cli_main.add_command(gui.gui_command)
