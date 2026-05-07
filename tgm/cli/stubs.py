import click


def stub_not_implemented(blocking_epic: str) -> None:
    raise click.ClickException(f"Not yet implemented (depends on {blocking_epic})")
