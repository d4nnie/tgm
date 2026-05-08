import logging

import click

from tgm.cli import aboutme, auth, chat, criteria, digest, gui, highlight, llm, watch
from tgm.shell.db import apply_migrations, open_database
from tgm.shell.logging import setup_logging
from tgm.shell.platform import ensure_user_data_dir


@click.group(invoke_without_command=True, context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--debug-pii",
    is_flag=True,
    default=False,
    help="Disable PII redaction in logs (development only).",
)
@click.pass_context
def cli_main(context: click.Context, debug_pii: bool) -> None:
    """Telegram Monitor — personal desktop digest of Telegram chats."""
    user_data_dir = ensure_user_data_dir()
    setup_logging(user_data_dir, debug_pii=debug_pii)

    logger = logging.getLogger(__name__)
    logger.info("cli_started", extra={"command": context.invoked_subcommand or "gui"})

    handle = open_database()
    apply_migrations(handle.engine)
    context.obj = handle

    if context.invoked_subcommand is None:
        context.invoke(gui.gui_command)


cli_main.add_command(auth.auth_group)
cli_main.add_command(chat.chat_group)
cli_main.add_command(digest.digest_group)
cli_main.add_command(highlight.highlight_group)
cli_main.add_command(criteria.criteria_group)
cli_main.add_command(aboutme.about_me_group)
cli_main.add_command(llm.llm_group)
cli_main.add_command(watch.watch_command)
cli_main.add_command(gui.gui_command)
