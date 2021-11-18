from __future__ import annotations
import logging
from pathlib import Path
from typing import Optional
import click
from click_loglevel import LogLevel
from outgoing import Sender, from_config_file
from platformdirs import user_config_path
from .core import RepoNews
from .util import UserError, log

DEFAULT_CONFIG_FILE = user_config_path("reponews", "jwodder") / "config.toml"


@click.command()
@click.option(
    "-c",
    "--config",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=DEFAULT_CONFIG_FILE,
    show_default=True,
    help="Path to configuration file",
)
@click.option(
    "-l",
    "--log-level",
    type=LogLevel(),
    default=logging.WARNING,
    help="Set logging level  [default: WARNING]",
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
@click.option(
    "--save/--no-save",
    default=True,
    help="Whether to update the state file  [default: --save]",
)
def main(config: Path, log_level: int, mode: Optional[str], save: bool) -> None:
    """
    Send e-mails about new events on your GitHub repositories.

    Visit <https://github.com/jwodder/reponews> for more information.
    """
    logging.basicConfig(
        format="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
        level=log_level,
    )
    try:
        with RepoNews.from_config_file(config) as reponews:
            if (mode is None or mode == "print") and reponews.config.recipient is None:
                raise click.UsageError(
                    "reponews.recipient must be set when constructing an e-mail"
                )
            sender: Optional[Sender]
            if mode is None:
                # Fail early if the outgoing config is invalid or missing:
                sender = from_config_file(config, fallback=True)
                assert sender is not None
            else:
                sender = None
            events = reponews.get_new_activity()
            if events:
                if mode == "print":
                    print(reponews.compose_email(events))
                elif mode == "body":
                    print(reponews.compose_email_body(events))
                else:
                    log.info("Sending e-mail ...")
                    msg = reponews.compose_email(events)
                    assert sender is not None
                    with sender:
                        sender.send(msg)
            else:
                log.info("No new activity")
            if save:
                reponews.save_state()
    except UserError as e:
        raise click.UsageError(str(e))


if __name__ == "__main__":
    main()
