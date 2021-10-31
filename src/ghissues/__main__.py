from __future__ import annotations
from pathlib import Path
from typing import Optional
import click
from outgoing import from_config_file
from platformdirs import user_config_path
from .core import GHIssues

DEFAULT_CONFIG_FILE = user_config_path("ghissues", "jwodder") / "config.toml"


@click.command()
@click.option(
    "-c",
    "--config",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=DEFAULT_CONFIG_FILE,
    show_default=True,
)
@click.option(
    "--print", "mode", flag_value="print", help="Output e-mail instead of sending"
)
@click.option(
    "--print-body",
    "mode",
    flag_value="body",
    help="Output e-mail body instead of sending",
)
@click.option("--save/--no-save", default=True, help="Whether to update the state file")
def main(mode: Optional[str], save: bool, config: Path) -> None:
    ghissues = GHIssues.from_config_file(config)
    events = ghissues.get_new_events()
    if events:
        msg = ghissues.compose_email(events)
        if mode == "print":
            print(msg)
        elif mode == "body":
            print(msg.get_content())
        else:
            with from_config_file(config, fallback=True) as sender:
                sender.send(msg)
    if save:
        ghissues.save_state()


if __name__ == "__main__":
    main()
