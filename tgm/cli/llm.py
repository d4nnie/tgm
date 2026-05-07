import click

from tgm.cli.stubs import stub_not_implemented


@click.group(name="llm")
def llm_group() -> None:
    """LLM provider commands."""


@llm_group.command(name="test")
def llm_test() -> None:
    """Ping the configured provider; print latency and model."""
    stub_not_implemented("EPIC-05 (LLM provider)")
