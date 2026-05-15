import json
from datetime import UTC, datetime

import click

from tgm.cli.stubs import stub_not_implemented
from tgm.core.scopes import parse_chat_scope
from tgm.shell.db import DatabaseHandle
from tgm.shell.repos import insert_feedback, is_chat_known


@click.group(name="highlight")
def highlight_group() -> None:
    """Highlights: list and mark-important."""


@highlight_group.command(name="list")
@click.option("--scope", type=str, required=True, help="`chat:<id>` | global.")
@click.option("--unseen", is_flag=True, default=False, help="Only unseen highlights.")
def highlight_list(scope: str, unseen: bool) -> None:
    """Print highlights as JSON. Scope is always in CLI form (chat:<id> | global)."""
    stub_not_implemented("EPIC-07 (worker tick produces digests with highlights)")


@highlight_group.command(name="mark-important")
@click.argument("message_ids", type=int, nargs=-1, required=True)
@click.option(
    "--scope",
    type=str,
    required=True,
    help="`chat:<id>` for per-chat criteria, `global` for global criteria (requires --chat-id).",
)
@click.option("--chat-id", type=int, default=None, help="Chat the messages belong to (required for --scope global).")
@click.option("--comment", type=str, default="", help="Free-form feedback comment.")
@click.pass_obj
def highlight_mark_important(
    handle: DatabaseHandle,
    message_ids: tuple[int, ...],
    scope: str,
    chat_id: int | None,
    comment: str,
) -> None:
    """Record a feedback marker. Scope in stdout JSON is always CLI form."""
    scope_kind, resolved_chat_id = _resolve_scope(scope, chat_id)
    user_comment = comment if comment else None
    with handle.session_factory() as session:
        if not is_chat_known(session, resolved_chat_id):
            raise click.ClickException(
                f"Chat {resolved_chat_id} not under monitoring; add it first with 'tgm chat add'"
            )
        feedback_id = insert_feedback(
            session,
            chat_id=resolved_chat_id,
            message_ids=list(message_ids),
            user_comment=user_comment,
            scope=scope_kind,
            marked_at=datetime.now(UTC),
        )
        session.commit()
    click.echo(
        json.dumps(
            {
                "feedback_id": feedback_id,
                "chat_id": resolved_chat_id,
                "message_ids": list(message_ids),
                "scope": scope,
                "user_comment": user_comment,
                "consumed": False,
            },
            ensure_ascii=False,
        )
    )


def _resolve_scope(scope: str, chat_id_option: int | None) -> tuple[str, int]:
    try:
        kind, parsed_chat_id = parse_chat_scope(scope)
    except ValueError as error:
        raise click.BadParameter(str(error)) from error
    if kind == "chat":
        if parsed_chat_id is None:
            raise click.BadParameter(f"--scope chat:<id> must have integer id; got {scope!r}")
        return "chat", parsed_chat_id
    if chat_id_option is None:
        raise click.UsageError("--chat-id is required when --scope=global")
    return "global", chat_id_option
