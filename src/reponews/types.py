# We can't use `from __future__ import annotations` here yet due to a bug in
# pydantic under Python 3.9.8:
# <https://github.com/samuelcolvin/pydantic/issues/3401>
from abc import abstractmethod
from datetime import datetime
from enum import Enum
import json
from typing import Any, ClassVar, Dict, Optional, Type
from eletter import reply_quote
from pydantic import BaseModel
from .qlobjs import (
    DISCUSSION_CONNECTION,
    DISCUSSION_LAST_CONNECTION,
    FORK_CONNECTION,
    FORK_LAST_CONNECTION,
    ISSUE_CONNECTION,
    ISSUE_LAST_CONNECTION,
    PR_CONNECTION,
    PR_LAST_CONNECTION,
    RELEASE_CONNECTION,
    RELEASE_LAST_CONNECTION,
    STAR_CONNECTION,
    STAR_LAST_CONNECTION,
    TAG_CONNECTION,
    TAG_LAST_CONNECTION,
    Object,
)
from .util import BogusEventError, T, log


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


class RepoActivity(Event):
    CONNECTION: ClassVar[Object]
    LAST_CONNECTION: ClassVar[Object]

    @classmethod
    @abstractmethod
    def from_node(cls: Type[T], _repo: Repository, node: Dict[str, Any]) -> T:
        ...

    @property
    @abstractmethod
    def logmsg(self) -> str:
        ...

    @property
    @abstractmethod
    def is_mine(self) -> bool:
        ...


class NewIssueoidEvent(RepoActivity):
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

    @property
    def logmsg(self) -> str:
        return f"{self.TYPE} #{self.number}: {self.title!r}"

    @property
    def is_mine(self) -> bool:
        return self.author.isViewer

    def __str__(self) -> str:
        return (
            f"[{self.repo.nameWithOwner}] {self.TYPE.upper()} #{self.number}:"
            f" {self.title} (@{self.author.login})\n<{self.url}>"
        )


class NewIssueEvent(NewIssueoidEvent):
    CONNECTION = ISSUE_CONNECTION
    LAST_CONNECTION = ISSUE_LAST_CONNECTION
    TYPE = "issue"


class NewPREvent(NewIssueoidEvent):
    CONNECTION = PR_CONNECTION
    LAST_CONNECTION = PR_LAST_CONNECTION
    TYPE = "pr"


class NewDiscussionEvent(NewIssueoidEvent):
    CONNECTION = DISCUSSION_CONNECTION
    LAST_CONNECTION = DISCUSSION_LAST_CONNECTION
    TYPE = "discussion"


class NewReleaseEvent(RepoActivity):
    CONNECTION = RELEASE_CONNECTION
    LAST_CONNECTION = RELEASE_LAST_CONNECTION
    name: Optional[str]
    tagName: str
    author: Optional[User]
    description: Optional[str]
    descriptionHTML: Optional[str]
    isDraft: bool
    isPrerelease: bool
    url: str

    @classmethod
    def from_node(cls, repo: Repository, node: Dict[str, Any]) -> "NewReleaseEvent":
        log.debug("Constructing %s from node: %s", cls.__name__, json.dumps(node))
        node["timestamp"] = node.pop("createdAt")
        node["repo"] = repo
        return cls.parse_obj(node)

    @property
    def logmsg(self) -> str:
        return f"release {self.tagName}: {self.name!r}"

    @property
    def is_mine(self) -> bool:
        return self.author is not None and self.author.isViewer

    def __str__(self) -> str:
        s = f"[{self.repo.nameWithOwner}] RELEASE {self.tagName}"
        if self.isDraft:
            s += " [draft]"
        if self.isPrerelease:
            s += " [prerelease]"
        if self.name:
            s += f": {self.name}"
        if self.author is not None:
            s += f" (@{self.author.login})"
        s += f"\n<{self.url}>"
        if self.description:
            s += "\n" + reply_quote(self.description).rstrip("\n")
        return s


class NewTagEvent(RepoActivity):
    CONNECTION = TAG_CONNECTION
    LAST_CONNECTION = TAG_LAST_CONNECTION
    name: str
    user: Optional[User]

    @classmethod
    def from_node(cls, repo: Repository, node: Dict[str, Any]) -> "NewTagEvent":
        log.debug("Constructing %s from node: %s", cls.__name__, json.dumps(node))
        target = node.pop("target")
        if target["__typename"] == "Commit":
            if target["committedDate"] is None:
                raise BogusEventError(
                    "Commit for tag {node['name']} does not have committedDate set"
                )
            node["timestamp"] = target["committedDate"]
            if target["author"] is not None:
                node["user"] = target["author"]["user"]
            else:
                node["user"] = None
        elif target["__typename"] == "Tag":
            if target["tagger"] is None or target["tagger"]["date"] is None:
                raise BogusEventError("Tag {node['name']} does not have date set")
            node["timestamp"] = target["tagger"]["date"]
            node["user"] = target["tagger"]["user"]
        else:
            raise BogusEventError(
                f"Tag {node['name']} is neither an annotated tag nor a pointer"
                " to a commit"
            )
        node["repo"] = repo
        return cls.parse_obj(node)

    @property
    def logmsg(self) -> str:
        return f"tag {self.name}"

    @property
    def is_mine(self) -> bool:
        return self.user is not None and self.user.isViewer

    def __str__(self) -> str:
        s = f"[{self.repo.nameWithOwner}] TAG {self.name}"
        if self.user is not None:
            s += f" (@{self.user.login})"
        s += f"\n<{self.repo.url}/releases/tag/{self.name}>"
        return s


class NewStarEvent(RepoActivity):
    CONNECTION = STAR_CONNECTION
    LAST_CONNECTION = STAR_LAST_CONNECTION
    user: User

    @classmethod
    def from_node(cls, repo: Repository, node: Dict[str, Any]) -> "NewStarEvent":
        log.debug("Constructing %s from node: %s", cls.__name__, json.dumps(node))
        node["timestamp"] = node.pop("starredAt")
        node["repo"] = repo
        return cls.parse_obj(node)

    @property
    def logmsg(self) -> str:
        return f"star by @{self.user.login}"

    @property
    def is_mine(self) -> bool:
        return self.user.isViewer

    def __str__(self) -> str:
        return f"★ @{self.user.login} starred {self.repo.nameWithOwner}"


class NewForkEvent(RepoActivity):
    CONNECTION = FORK_CONNECTION
    LAST_CONNECTION = FORK_LAST_CONNECTION
    fork: Repository

    @classmethod
    def from_node(cls, repo: Repository, node: Dict[str, Any]) -> "NewForkEvent":
        log.debug("Constructing %s from node: %s", cls.__name__, json.dumps(node))
        timestamp = node.pop("createdAt")
        return cls(timestamp=timestamp, repo=repo, fork=node)

    @property
    def logmsg(self) -> str:
        return f"fork by @{self.fork.owner.login}"

    @property
    def is_mine(self) -> bool:
        return self.fork.owner.isViewer

    def __str__(self) -> str:
        return (
            f"@{self.fork.owner.login} forked {self.repo.nameWithOwner}\n"
            f"<{self.fork.url}>"
        )


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
    old_repo: Repository

    def __str__(self) -> str:
        return (
            f"Repository renamed: {self.old_repo.nameWithOwner} →"
            f" {self.repo.nameWithOwner}"
        )


class ActivityType(Enum):
    ISSUE = ("issue", "issues", NewIssueEvent)
    PR = ("pr", "pullRequests", NewPREvent)
    DISCUSSION = ("discussion", "discussions", NewDiscussionEvent)
    RELEASE = ("release", "releases", NewReleaseEvent)
    TAG = ("tag", "tags", NewTagEvent)
    STAR = ("star", "stargazers", NewStarEvent)
    FORK = ("fork", "forks", NewForkEvent)

    def __new__(cls, value: str, _api_name: str, _event_cls: type) -> "ActivityType":
        obj = object.__new__(cls)
        obj._value_ = value
        return obj  # type: ignore[no-any-return]

    def __init__(
        self, _value: str, api_name: str, event_cls: Type[RepoActivity]
    ) -> None:
        self.api_name = api_name
        self.event_cls = event_cls


CursorDict = Dict[ActivityType, Optional[str]]
