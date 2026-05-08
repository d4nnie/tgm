import json
from datetime import UTC, datetime

import click

from tgm.cli.stubs import stub_not_implemented
from tgm.shell.db import DatabaseHandle
from tgm.shell.repos import insert_feedback


@click.group(name="highlight")
def highlight_group() -> None:
    """Highlights: list and mark-important."""


@highlight_group.command(name="list")
@click.argument("scope", type=str)
@click.option("--unseen", is_flag=True, default=False, help="Only unseen highlights.")
def highlight_list(scope: str, unseen: bool) -> None:
    """Print highlights as JSON."""
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
    """Record a feedback marker for the given message ids."""
    scope_kind, resolved_chat_id = _resolve_scope(scope, chat_id)
    user_comment = comment if comment else None
    with handle.session_factory() as session:
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
                "scope": scope_kind,
                "user_comment": user_comment,
                "consumed": False,
            },
            ensure_ascii=False,
        )
    )


def _resolve_scope(scope: str, chat_id_option: int | None) -> tuple[str, int]:
    if scope.startswith("chat:"):
        try:
            return "chat", int(scope[len("chat:") :])
        except ValueError as error:
            raise click.BadParameter(f"--scope chat:<id> must have integer id; got {scope!r}") from error
    if scope == "global":
        if chat_id_option is None:
            raise click.UsageError("--chat-id is required when --scope=global")
        return "global", chat_id_option
    raise click.BadParameter(f"--scope must be 'chat:<id>' or 'global'; got {scope!r}")
