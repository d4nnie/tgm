import json

import click

from tgm.shell.db import DatabaseHandle
from tgm.shell.repos import get_user_profile_about_me, upsert_user_profile_about_me


@click.group(name="about-me")
def about_me_group() -> None:
    """User self-description used in prompts."""


@about_me_group.command(name="show")
@click.pass_obj
def about_me_show(handle: DatabaseHandle) -> None:
    """Print current about-me text."""
    with handle.session_factory() as session:
        text = get_user_profile_about_me(session)
    click.echo(json.dumps({"about_me": text}, ensure_ascii=False))


@about_me_group.command(name="set")
@click.argument("text", type=str)
@click.pass_obj
def about_me_set(handle: DatabaseHandle, text: str) -> None:
    """Replace about-me text."""
    with handle.session_factory() as session:
        upsert_user_profile_about_me(session, text)
        session.commit()
    click.echo(json.dumps({"about_me": text}, ensure_ascii=False))
