# We can't use `from __future__ import annotations` here yet due to a bug in
# pydantic under Python 3.9.8:
# <https://github.com/samuelcolvin/pydantic/issues/3401>
from datetime import datetime
from enum import Enum
import json
from typing import Any, ClassVar, Dict, Optional, Type
from eletter import reply_quote
from pydantic import BaseModel
from .qlobjs import DISCUSSION_CONNECTION, ISSUE_CONNECTION, PR_CONNECTION, Object
from .util import log


class Affiliation(Enum):
    OWNER = "OWNER"
    ORGANIZATION_MEMBER = "ORGANIZATION_MEMBER"
    COLLABORATOR = "COLLABORATOR"


class User(BaseModel):
    # `name` is None/unset when the user is a bot or they never set their
    # display name
    name: Optional[str] = None
    login: str
    url: str
    isViewer: bool = False

    @classmethod
    def from_node(cls, node: Dict[str, Any]) -> "User":
        log.debug("Constructing User from node: %s", json.dumps(node))
        return cls.parse_obj(node)

    def __str__(self) -> str:
        return self.login


class Repository(BaseModel):
    id: str
    owner: User
    name: str
    nameWithOwner: str
    url: str
    description: Optional[str]
    descriptionHTML: str

    @classmethod
    def from_node(cls, node: Dict[str, Any]) -> "Repository":
        log.debug("Constructing Repository from node: %s", json.dumps(node))
        return cls.parse_obj(node)

    def __str__(self) -> str:
        return self.nameWithOwner


class Event(BaseModel):
    timestamp: datetime  # Used for sorting
    repo: Repository


class NewIssueoidEvent(Event):
    CONNECTION: ClassVar[Object]
    TYPE: ClassVar[str]
    number: int
    title: str
    author: User
    url: str

    @classmethod
    def from_node(cls, repo: Repository, node: Dict[str, Any]) -> "NewIssueoidEvent":
        log.debug("Constructing %s from node: %s", cls.__name__, json.dumps(node))
        node["timestamp"] = node.pop("createdAt")
        node["repo"] = repo
        return cls.parse_obj(node)

    def __str__(self) -> str:
        return (
            f"[{self.repo.nameWithOwner}] {self.TYPE.upper()} #{self.number}:"
            f" {self.title} (@{self.author.login})\n<{self.url}>"
        )


class NewIssueEvent(NewIssueoidEvent):
    CONNECTION = ISSUE_CONNECTION
    TYPE = "issue"


class NewPREvent(NewIssueoidEvent):
    CONNECTION = PR_CONNECTION
    TYPE = "pr"


class NewDiscussionEvent(NewIssueoidEvent):
    CONNECTION = DISCUSSION_CONNECTION
    TYPE = "discussion"


class RepoTrackedEvent(Event):
    def __str__(self) -> str:
        s = f"Now tracking repository {self.repo.nameWithOwner}\n<{self.repo.url}>"
        if self.repo.description:
            s += "\n" + reply_quote(self.repo.description).rstrip("\n")
        return s


class RepoUntrackedEvent(Event):
    def __str__(self) -> str:
        return f"No longer tracking repository {self.repo.nameWithOwner}"


class RepoRenamedEvent(Event):
    old_nameWithOwner: str

    def __str__(self) -> str:
        return (
            f"Repository renamed: {self.old_nameWithOwner} → {self.repo.nameWithOwner}"
        )


class IssueoidType(Enum):
    ISSUE = ("issue", "issues", NewIssueEvent)
    PR = ("pr", "pullRequests", NewPREvent)
    DISCUSSION = ("discussion", "discussions", NewDiscussionEvent)

    def __new__(cls, value: str, _api_name: str, _event_cls: type) -> "IssueoidType":
        obj = object.__new__(cls)
        obj._value_ = value
        return obj  # type: ignore[no-any-return]

    def __init__(
        self, _value: str, api_name: str, event_cls: Type[NewIssueoidEvent]
    ) -> None:
        self.api_name = api_name
        self.event_cls = event_cls


CursorDict = Dict[IssueoidType, Optional[str]]
