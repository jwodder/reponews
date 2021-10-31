from __future__ import annotations
from datetime import datetime
from enum import Enum
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

    @property
    def new_event(self) -> NewRepoEvent:
        return NewRepoEvent(
            timestamp=datetime.now().astimezone(),
            repo_fullname=self.fullname,
            url=self.url,
        )


class Event(BaseModel):
    timestamp: datetime  # Used for sorting
    repo: Repository


class NewIssueoidEvent(Event):
    type: IssueoidType
    repo: Repository
    number: int
    title: str
    author: str
    url: str

    def __str__(self) -> str:
        return (
            f"[{self.repo.fullname}] {self.type.value.upper()} #{self.number}:"
            f" {self.title} (@{self.author})\n<{self.url}>"
        )


class NewRepoEvent(Event):
    url: str

    def __str__(self) -> str:
        return f"Now tracking repository {self.repo.fullname}\n<{self.url}>"


class RepoRemovedEvent(Event):
    def __str__(self) -> str:
        return f"Repository {self.repo.fullname} not found; no longer tracking"
