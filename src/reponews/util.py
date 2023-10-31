from __future__ import annotations
import logging
from pathlib import Path
import platform
import re
from typing import TypeVar
from platformdirs import user_state_path
from pydantic import AnyHttpUrl, TypeAdapter
import requests
from . import __url__, __version__

T = TypeVar("T")


log = logging.getLogger(__package__)

MAIL_USER_AGENT = f"reponews/{__version__} ({__url__})"

HTTP_USER_AGENT = "reponews/{} ({}) requests/{} {}/{}".format(
    __version__,
    __url__,
    requests.__version__,
    platform.python_implementation(),
    platform.python_version(),
)


def mkalias(s: str) -> str:
    return s.replace("_", "-")


def get_default_state_file() -> Path:
    return user_state_path("reponews", "jwodder") / "state.json"


def dos2unix(s: str) -> str:
    return re.sub(r"\r\n?", "\n", s)


def default_api_url() -> AnyHttpUrl:
    adapter = TypeAdapter(AnyHttpUrl)
    return adapter.validate_python("https://api.github.com/graphql")


class NotFoundError(Exception):
    pass


class BogusEventError(Exception):
    pass


class UserError(Exception):
    pass
