from __future__ import annotations
from enum import Enum
from pathlib import Path
from platformdirs import user_state_path


class IssueoidType(Enum):
    ISSUE = ("issue", "issues")
    PR = ("pr", "pullRequests")
    DISCUSSION = ("discussion", "discussions")

    def __new__(cls, value: str, _api_name: str) -> IssueoidType:
        obj = object.__new__(cls)
        obj._value_ = value
        return obj  # type: ignore[no-any-return]

    def __init__(self, _value: str, api_name: str) -> None:
        self.api_name = api_name


class Affiliation(Enum):
    OWNER = "OWNER"
    ORGANIZATION_MEMBER = "ORGANIZATION_MEMBER"
    COLLABORATOR = "COLLABORATOR"


def expanduser(v: Path) -> Path:
    # We have to define a function instead of yielding `Path.expanduser` from
    # `__get_validators__` because pydantic complains about the unbound method
    # having `self` as an argument name.
    return v.expanduser()


def mkalias(s: str) -> str:
    return s.replace("_", "-")


def get_default_state_file() -> Path:
    return user_state_path("ghissues", "jwodder") / "state.json"
