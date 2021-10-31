from __future__ import annotations
from pathlib import Path
from platformdirs import user_state_path


def expanduser(v: Path) -> Path:
    # We have to define a function instead of yielding `Path.expanduser` from
    # `__get_validators__` because pydantic complains about the unbound method
    # having `self` as an argument name.
    return v.expanduser()


def mkalias(s: str) -> str:
    return s.replace("_", "-")


def get_default_state_file() -> Path:
    return user_state_path("ghissues", "jwodder") / "state.json"
