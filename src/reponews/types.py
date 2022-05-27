from __future__ import annotations
from abc import abstractmethod
from datetime import datetime
from enum import Enum
import json
import sys
from typing import Any, ClassVar, Dict, Optional, Type
from eletter import reply_quote
from pydantic import BaseModel, validator
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
from .util import BogusEventError, T, dos2unix, log

if sys.version_info[:2] >= (3, 8):
    from typing import Literal
else:
    from typing_extensions import Literal


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
    def from_node(cls, node: Dict[str, Any]) -> Repository:
        log.debug("Constructing Repository from node: %s", json.dumps(node))
        return cls.parse_obj(node)

    def __str__(self) -> str:
        return self.nameWithOwner


class Event(BaseModel):
    event_type: str
    timestamp: datetime  # Used for sorting
    repo: Repository

    @abstractmethod
    def render(self) -> str:
        ...


class RepoActivity(Event):
    CONNECTION: ClassVar[Object]
    LAST_CONNECTION: ClassVar[Object]

    @classmethod
    @abstractmethod
    def from_node(cls: Type[T], _repo: Repository, node: Dict[str, Any]) -> T:
        ...

    @property
    @abstractmethod
    def is_mine(self) -> bool:
        ...


class NewIssueoidEvent(RepoActivity):
    number: int
    title: str
    author: User
    url: str

    @classmethod
    def from_node(cls, repo: Repository, node: Dict[str, Any]) -> NewIssueoidEvent:
        log.debug("Constructing %s from node: %s", cls.__name__, json.dumps(node))
        node["timestamp"] = node.pop("createdAt")
        node["repo"] = repo
        return cls.parse_obj(node)

    def render(self) -> str:
        return (
            f"[{self.repo.nameWithOwner}] {self.event_type.upper()} #{self.number}:"
            f" {self.title} (@{self.author.login})\n<{self.url}>"
        )

    @property
    def is_mine(self) -> bool:
        return self.author.isViewer

    def __str__(self) -> str:
        return f"{self.event_type} #{self.number}: {self.title!r}"


class NewIssueEvent(NewIssueoidEvent):
    CONNECTION = ISSUE_CONNECTION
    LAST_CONNECTION = ISSUE_LAST_CONNECTION
    event_type: Literal["issue"] = "issue"


class NewPREvent(NewIssueoidEvent):
    CONNECTION = PR_CONNECTION
    LAST_CONNECTION = PR_LAST_CONNECTION
    event_type: Literal["pr"] = "pr"


class NewDiscussionEvent(NewIssueoidEvent):
    CONNECTION = DISCUSSION_CONNECTION
    LAST_CONNECTION = DISCUSSION_LAST_CONNECTION
    event_type: Literal["discussion"] = "discussion"


class NewReleaseEvent(RepoActivity):
    CONNECTION = RELEASE_CONNECTION
    LAST_CONNECTION = RELEASE_LAST_CONNECTION
    event_type: Literal["release"] = "release"
    name: Optional[str]
    tagName: str
    author: Optional[User]
    description: Optional[str]
    descriptionHTML: Optional[str]
    isDraft: bool
    isPrerelease: bool
    url: str

    @validator("description")
    def _dos2unix(cls, v: Optional[str]) -> Optional[str]:  # noqa: B902, U100
        return dos2unix(v) if v is not None else None

    @classmethod
    def from_node(cls, repo: Repository, node: Dict[str, Any]) -> NewReleaseEvent:
        log.debug("Constructing %s from node: %s", cls.__name__, json.dumps(node))
        node["timestamp"] = node.pop("createdAt")
        node["repo"] = repo
        return cls.parse_obj(node)

    def render(self) -> str:
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

    @property
    def is_mine(self) -> bool:
        return self.author is not None and self.author.isViewer

    def __str__(self) -> str:
        return f"release {self.tagName}: {self.name!r}"


class NewTagEvent(RepoActivity):
    CONNECTION = TAG_CONNECTION
    LAST_CONNECTION = TAG_LAST_CONNECTION
    event_type: Literal["tag"] = "tag"
    name: str
    user: Optional[User]

    @classmethod
    def from_node(cls, repo: Repository, node: Dict[str, Any]) -> NewTagEvent:
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

    def render(self) -> str:
        s = f"[{self.repo.nameWithOwner}] TAG {self.name}"
        if self.user is not None:
            s += f" (@{self.user.login})"
        s += f"\n<{self.repo.url}/releases/tag/{self.name}>"
        return s

    @property
    def is_mine(self) -> bool:
        return self.user is not None and self.user.isViewer

    def __str__(self) -> str:
        return f"tag {self.name}"


class NewStarEvent(RepoActivity):
    CONNECTION = STAR_CONNECTION
    LAST_CONNECTION = STAR_LAST_CONNECTION
    event_type: Literal["star"] = "star"
    user: User

    @classmethod
    def from_node(cls, repo: Repository, node: Dict[str, Any]) -> NewStarEvent:
        log.debug("Constructing %s from node: %s", cls.__name__, json.dumps(node))
        node["timestamp"] = node.pop("starredAt")
        node["repo"] = repo
        return cls.parse_obj(node)

    def render(self) -> str:
        return f"★ @{self.user.login} starred {self.repo.nameWithOwner}"

    @property
    def is_mine(self) -> bool:
        return self.user.isViewer

    def __str__(self) -> str:
        return f"star by @{self.user.login}"


class NewForkEvent(RepoActivity):
    CONNECTION = FORK_CONNECTION
    LAST_CONNECTION = FORK_LAST_CONNECTION
    event_type: Literal["fork"] = "fork"
    fork: Repository

    @classmethod
    def from_node(cls, repo: Repository, node: Dict[str, Any]) -> NewForkEvent:
        log.debug("Constructing %s from node: %s", cls.__name__, json.dumps(node))
        timestamp = node.pop("createdAt")
        return cls(timestamp=timestamp, repo=repo, fork=node)

    def render(self) -> str:
        return (
            f"@{self.fork.owner.login} forked {self.repo.nameWithOwner}\n"
            f"<{self.fork.url}>"
        )

    @property
    def is_mine(self) -> bool:
        return self.fork.owner.isViewer

    def __str__(self) -> str:
        return f"fork by @{self.fork.owner.login}"


class RepoTrackedEvent(Event):
    event_type: Literal["tracked"] = "tracked"

    def render(self) -> str:
        s = f"Now tracking repository {self.repo.nameWithOwner}\n<{self.repo.url}>"
        if self.repo.description:
            s += "\n" + reply_quote(self.repo.description).rstrip("\n")
        return s


class RepoUntrackedEvent(Event):
    event_type: Literal["untracked"] = "untracked"

    def render(self) -> str:
        return f"No longer tracking repository {self.repo.nameWithOwner}"


class RepoRenamedEvent(Event):
    event_type: Literal["renamed"] = "renamed"
    old_repo: Repository

    def render(self) -> str:
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

    def __new__(cls, value: str, _api_name: str, _event_cls: type) -> ActivityType:
        obj = object.__new__(cls)
        obj._value_ = value
        return obj  # type: ignore[no-any-return]

    def __init__(
        self, _value: str, api_name: str, event_cls: Type[RepoActivity]
    ) -> None:
        self.api_name = api_name
        self.event_cls = event_cls


CursorDict = Dict[ActivityType, Optional[str]]
