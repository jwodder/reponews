from __future__ import annotations
import logging
from pathlib import Path
from typing import TypeVar
from platformdirs import user_state_path

T = TypeVar("T")


log = logging.getLogger("reponews")


def expanduser(v: Path) -> Path:
    # We have to define a function instead of yielding `Path.expanduser` from
    # `__get_validators__` because pydantic complains about the unbound method
    # having `self` as an argument name.
    return v.expanduser()


def mkalias(s: str) -> str:
    return s.replace("_", "-")


def get_default_state_file() -> Path:
    return user_state_path("reponews", "jwodder") / "state.json"


class NotFoundError(Exception):
    pass


class BogusEventError(Exception):
    pass
