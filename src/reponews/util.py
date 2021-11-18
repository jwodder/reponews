from __future__ import annotations
import logging
from pathlib import Path
from typing import TypeVar
from platformdirs import user_state_path

T = TypeVar("T")


log = logging.getLogger("reponews")


def mkalias(s: str) -> str:
    return s.replace("_", "-")


def get_default_state_file() -> Path:
    return user_state_path("reponews", "jwodder") / "state.json"


class NotFoundError(Exception):
    pass


class BogusEventError(Exception):
    pass


class UserError(Exception):
    pass
