from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from eletter import reply_quote
from pydantic import BaseModel


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


class Repository(BaseModel):
    id: str
    owner: str
    name: str
    fullname: str
    url: str
    description: Optional[str]
    descriptionHTML: str

    @classmethod
    def from_node(cls, node: Dict[str, Any]) -> Repository:
        return cls(
            id=node["id"],
            owner=node["owner"]["login"],
            name=node["name"],
            fullname=node["nameWithOwner"],
            url=node["url"],
            description=node["description"],
            descriptionHTML=node["descriptionHTML"],
        )

    def __str__(self) -> str:
        return self.fullname


class User(BaseModel):
    name: str
    login: str
    url: str
    is_me: bool

    @classmethod
    def from_node(cls, node: Dict[str, Any]) -> User:
        return cls(
            name=node.get("name", node["login"]),  # Bots don't have names
            login=node["login"],
            url=node["url"],
            is_me=node.get("isViewer", False),
        )


class Event(BaseModel):
    timestamp: datetime  # Used for sorting


class NewIssueoidEvent(Event):
    type: IssueoidType
    repo: Repository
    number: int
    title: str
    author: User
    url: str

    @classmethod
    def from_node(
        cls, type: IssueoidType, repo: Repository, node: Dict[str, Any]
    ) -> NewIssueoidEvent:
        return cls(
            type=type,
            repo=repo,
            timestamp=node["createdAt"],
            number=node["number"],
            title=node["title"],
            author=User.from_node(node["author"]),
            url=node["url"],
        )

    def __str__(self) -> str:
        return (
            f"[{self.repo.fullname}] {self.type.value.upper()} #{self.number}:"
            f" {self.title} (@{self.author.login})\n<{self.url}>"
        )


class RepoTrackedEvent(Event):
    repo: Repository

    def __str__(self) -> str:
        s = f"Now tracking repository {self.repo.fullname}\n<{self.repo.url}>"
        if self.repo.description:
            s += "\n" + reply_quote(self.repo.description)
        return s


class RepoUntrackedEvent(Event):
    repo_fullname: str

    def __str__(self) -> str:
        return f"No longer tracking repository {self.repo_fullname}"


class RepoRenamedEvent(Event):
    repo: Repository
    old_fullname: str

    def __str__(self) -> str:
        return f"Repository renamed: {self.old_fullname} → {self.repo.fullname}"
