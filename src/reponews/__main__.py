from __future__ import annotations
from enum import Enum
import json
import logging
from pathlib import Path
from typing import Optional
import click
from click_loglevel import LogLevel
from dotenv import find_dotenv, load_dotenv
from outgoing import Sender, from_config_file
from platformdirs import user_config_path
from . import __version__
from .core import RepoNews
from .util import UserError, log

DEFAULT_CONFIG_FILE = user_config_path("reponews", "jwodder") / "config.toml"

Mode = Enum("Mode", "PRINT PRINT_BODY DUMP_REPOS")


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(
    __version__,
    "-V",
    "--version",
    message="%(prog)s %(version)s",
)
@click.option(
    "-c",
    "--config",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=DEFAULT_CONFIG_FILE,
    show_default=True,
    help="Path to configuration file",
)
@click.option(
    "--dump-repos",
    "mode",
    flag_value=Mode.DUMP_REPOS,
    type=click.UNPROCESSED,
    help="List tracked repos and their activity preferences",
)
@click.option(
    "-E",
    "--env",
    type=click.Path(exists=True, dir_okay=False),
    help="Load environment variables from given .env file",
)
@click.option(
    "-l",
    "--log-level",
    type=LogLevel(),
    default="WARNING",
    help="Set logging level",
    show_default=True,
)
@click.option(
    "--print",
    "mode",
    flag_value=Mode.PRINT,
    type=click.UNPROCESSED,
    help="Output e-mail instead of sending",
)
@click.option(
    "--print-body",
    "mode",
    flag_value=Mode.PRINT_BODY,
    type=click.UNPROCESSED,
    help="Output e-mail body instead of sending",
)
@click.option(
    "--save/--no-save",
    default=True,
    help="Whether to update the state file  [default: --save]",
)
def main(
    config: Path, log_level: int, mode: Optional[Mode], save: bool, env: Optional[str]
) -> None:
    """
    Send e-mails about new events on your GitHub repositories.

    Visit <https://github.com/jwodder/reponews> for more information.
    """
    if env is None:
        env = find_dotenv(usecwd=True)
    load_dotenv(env)
    logging.basicConfig(
        format="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
        level=log_level,
    )
    try:
        with RepoNews.from_config_file(config) as reponews:
            if mode is Mode.DUMP_REPOS:
                print(json.dumps(reponews.dump_repo_prefs(), indent=4, sort_keys=True))
                return
            if mode in (None, Mode.PRINT) and reponews.config.recipient is None:
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
                if mode is Mode.PRINT:
                    print(reponews.compose_email(events))
                elif mode is Mode.PRINT_BODY:
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
    main()  # pragma: no cover
